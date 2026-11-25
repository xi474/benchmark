"""Bounded recovery driven only by executed, task-visible public validations.

Output churn is not a repair. Failures are tracked across intervening actions
using a check identity, diagnostic signature and observed source/import closure.
No model request, hidden evaluator, task taxonomy or predeclared DAG is used.
"""
import ast
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import re
import shlex
import time

VERSION = 'public-validation-progress-v1'
REPEAT_LIMIT = 3
SAME_FAILURE_LIMIT = 5
RECOVERY_TURNS = 6
RECOVERY_EPISODES = 2
CONTROL = frozenset({'report_frontier_state', 'spawn_subtasks',
                     'choose_execution_mode', 'choose_execution_mode_v2'})
FRAME = re.compile(r'File "([^"]+\.py)", line \d+')
EXCEPTION = re.compile(r'(?m)^(?:[\w.]+(?:Error|Exception|Failure|Exit)|AssertionError):.*$')
MISSING_FILE = re.compile(r"""(?m)^FileNotFoundError: \[Errno 2\] [^\n]*?: (['"])([^\n]+?)\1\s*$""")


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


class ValidationProgressMixin:
    def _validation_progress_init(self):
        self._vp_initial = None
        self._vp_ast = {}
        self._vp_records = {}
        self._vp_episodes = {}
        self._vp_active = None
        self._vp_before = None
        self._vp_seconds = 0.0

    def _vp_snapshot(self):
        observer = getattr(self, '_cross_workspace', None)
        if observer is None:
            return {}, False
        _, certain = observer.snapshot()
        with observer.lock:
            files = {k: v[1] for k, v in observer.cache.items()}
        return files, certain

    def _vp_parse(self, relative, files):
        stamp = files.get(relative)
        key = (relative, stamp)
        if key in self._vp_ast:
            return self._vp_ast[key]
        result = (False, [])
        if stamp is not None:
            try:
                path = self._cross_workspace.root / relative
                if path.stat().st_size > 256_000 or path.is_symlink():
                    return result
                tree = ast.parse(path.read_text(encoding='utf-8-sig'))
                references = []
                validator = False
                for node in ast.walk(tree):
                    validator |= isinstance(node, ast.Assert)
                    if isinstance(node, (ast.Import, ast.ImportFrom)):
                        modules = [n.name for n in node.names] if isinstance(node, ast.Import) else [node.module or '']
                        if isinstance(node, ast.ImportFrom):
                            modules += ['.'.join(filter(None, [node.module, n.name]))
                                        for n in node.names if n.name != '*']
                        validator |= any(m.split('.')[0] in {'pytest', 'unittest'} for m in modules)
                        for module in modules:
                            base = Path(relative).parent
                            if isinstance(node, ast.ImportFrom) and node.level:
                                for _ in range(node.level - 1):
                                    base = base.parent
                            suffix = module.replace('.', '/')
                            for prefix in (base, Path('.')):
                                references += [(prefix / (suffix + '.py')).as_posix(),
                                               (prefix / suffix / '__init__.py').as_posix()]
                    if isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value.endswith('.py'):
                        for prefix in (Path(relative).parent, Path('.')):
                            references.append((prefix / node.value).as_posix())
                result = (validator, references)
            except (OSError, ValueError, SyntaxError, UnicodeError):
                pass
        if len(self._vp_ast) >= 512:
            self._vp_ast.clear()
        self._vp_ast[key] = result
        return result

    def _validation_progress_before_batch(self, state, calls):
        self._vp_before = None
        if not self.output_guard_enabled or not calls or all(c.name in CONTROL for c in calls):
            return
        started = time.perf_counter()
        files, certain = self._vp_snapshot()
        if self._vp_initial is None and certain:
            # Keep only hashes here. Parse a validator/import closure lazily
            # when an actual receipt references it, not the entire repository.
            # Share the initial task baseline, not recovery counters. A child
            # must not relabel parent-generated code as a provided validator.
            observer = self._cross_workspace
            with observer.lock:
                baseline = getattr(observer, '_validation_initial_sources', None)
                if baseline is None:
                    baseline = {p: h for p, h in files.items() if p.endswith('.py')}
                    observer._validation_initial_sources = baseline
                self._vp_initial = dict(baseline)
        self._vp_before = (files, certain, bool(self._vp_active))
        self._vp_seconds += time.perf_counter() - started

    def _vp_relative(self, value):
        try:
            path = Path(value)
            root = self._cross_workspace.root
            path = path if path.is_absolute() else root / path
            return path.resolve().relative_to(root).as_posix()
        except (ValueError, OSError):
            return None

    def _vp_invoked_checks(self, command, files):
        # A successful echo/string match is never validation evidence. Only
        # simple Python invocations (or an all-success && chain) qualify.
        if not isinstance(command, str) or re.search(r'[|;<>\n\r]|(?<!&)&(?!&)', command):
            return []
        checks = []
        for segment in command.split('&&'):
            try:
                words = shlex.split(segment, posix=False)
            except ValueError:
                continue
            if len(words) < 2 or not re.fullmatch(r'python(?:\d+(?:\.\d+)?)?(?:\.exe)?', Path(words[0].strip('"\'')).name, re.I):
                continue
            target = self._vp_relative(words[1].strip('"\''))
            if target in (self._vp_initial or {}) and self._vp_parse(target, files)[0]:
                checks.append(target)
        return checks

    def _vp_diagnostic(self, output):
        text = str(output or '')[-20_000:]
        root = str(self._cross_workspace.root)
        for prefix in (root.replace('\\', '\\\\'), root, root.replace('\\', '/')):
            text = text.replace(prefix, '<workspace>')
        text = re.sub(r'(?m)^\s*elapsed\s+[\d.eE+-]+\s*$', '', text)
        text = re.sub(r'(File "[^"\n]+", line )\d+', r'\1<line>', text)
        lines = EXCEPTION.findall(text)
        return '\n'.join(lines)[-2500:] if lines else text.strip()[-2500:]

    def _vp_sources(self, check, output, files):
        seeds = {check}
        for path in FRAME.findall(str(output or '')):
            relative = self._vp_relative(path)
            if relative in files:
                seeds.add(relative)
        pending = list(seeds)
        while pending and len(seeds) < 128:
            for reference in self._vp_parse(pending.pop(), files)[1]:
                if reference in files and reference not in seeds:
                    seeds.add(reference)
                    pending.append(reference)
        return sorted(seeds), not pending

    def _vp_root_dependency_evidence(self, check, output, files):
        if self.depth != 0:
            return None
        frames = list(dict.fromkeys(self._vp_relative(p) for p in FRAME.findall(str(output))))
        frames = [p for p in frames if p in files]
        if check not in frames:
            return None
        missing = {self._vp_relative(path) for _, path in MISSING_FILE.findall(str(output))}
        if len(missing) != 1:
            return None
        artifact, = missing
        if not artifact or artifact in files:
            return None

        contracts = [p for p in files if Path(p).name == 'contract.json'
                     and not any(part.startswith('.') for part in Path(p).parts)]
        if len(contracts) > 128:
            return None
        consumers = set()
        producers = set()
        frame_contracts = {Path(p).with_name('contract.json').as_posix() for p in frames}
        for relative in contracts:
            path = self._cross_workspace.root / relative
            try:
                if self._vp_relative(relative) != relative or path.stat().st_size > 64_000:
                    continue
                contract = json.loads(path.read_text(encoding='utf-8-sig'))
            except (OSError, ValueError, UnicodeError):
                continue
            if not isinstance(contract, dict):
                continue
            if contract.get('output') == artifact:
                producers.add(relative)
            inputs = contract.get('inputs')
            if relative in frame_contracts and isinstance(inputs, list) and artifact in inputs:
                consumers.add(relative)
        if len(consumers) != 1 or len(producers) != 1 or consumers == producers:
            return None
        consumer, = consumers
        producer, = producers
        evidence = {'missing_artifact': artifact, 'consumer_contract': consumer,
                    'producer_contract': producer, 'traceback_frames': frames[-12:]}
        entrypoints = [p for p in frames if p != check and Path(p).parent == Path(check).parent]
        if len(entrypoints) == 1:
            evidence['root_entrypoint_hint'] = entrypoints[0]
        return evidence

    def _vp_feedback(self, state, record, output, files):
        if getattr(self, '_hs_ticket', None) is not None:
            self._hs_discard('public_validation_recovery_required')
        note = {'check': record['check'], 'failure': record['diagnostic'][-1800:],
                'failure_sha256': record['failure'], 'source_version': record['version'],
                'observed_source_paths': record['sources'][:16],
                'same_failure_and_version_observations': record['repeat'],
                'recovery_episode': self._vp_episodes[record['check']],
                'maximum_business_batches': RECOVERY_TURNS,
                'instruction': 'The same public validation failure has not been repaired. '
                    'Diagnose its actual traceback and repair the responsible source or dependency. '
                    'Recreating outputs, repeating the check, editing unrelated files, or cycling back '
                    'to old source does not resolve it. Read the relevant source if needed, make a '
                    'targeted repair, and re-run this public validation from its required clean state. '
                    'Preserve all original contracts and checks. If unable to repair, explicitly '
                    'report the blocker using the controls available in this scope.',
                'evidence_scope': 'Executed public tool receipts and observed source/import closure only; no hidden verifier or preset DAG'}
        dependency = self._vp_root_dependency_evidence(record['check'], output, files)
        if dependency:
            note['root_integration_evidence'] = dependency
            note['evidence_scope'] = (
                'Executed public tool receipts, observed source/import closure and matching '
                'visible workspace contracts only; no hidden verifier or preset DAG')
            entrypoint = dependency.get('root_entrypoint_hint', 'the root entrypoint in the traceback')
            producer = dependency['producer_contract']
            consumer = dependency['consumer_contract']
            note['instruction'] = (
                f'First inspect the component execution order in {entrypoint}. '
                f'The producer in {producer} must execute before the consumer in {consumer}. '
                'If the entrypoint sorts paths and violates this dependency, fix the order '
                'in the entrypoint and preserve existing renderer arguments and working directories. '
                'If the order is already correct, diagnose the producer and its output path. '
                'Then run the original public check from clean outputs. '
                'A manually created artifact does not fix the entrypoint. '
                'Preserve the original contracts and checks. If unable to repair, report the blocker.')
        message = {'role': 'user', 'content': '[RUNTIME_VALIDATION_RECOVERY]\n' + json.dumps(note, ensure_ascii=False)}
        if dependency:
            record['root_feedback'] = (record['failure'], message)
        state.messages.append(message)
        self.tracer.emit('validation_progress_recovery_requested', scope_id=self.scope_id,
                         step=state.step, check=record['check'], failure_sha256=record['failure'],
                         source_version=record['version'], episode=self._vp_episodes[record['check']],
                         maximum_business_batches=RECOVERY_TURNS)

    def _vp_current_root_feedback(self):
        active = self._vp_active
        feedback = active.get('root_feedback') if self.depth == 0 and active else None
        if feedback and feedback[0] == active['failure'] and not active.get('final_recheck_pending'):
            return feedback[1]
        return None

    def _vp_business_request(self, state):
        if (state.v2_frontier_handshake_pending or state.pending_v2_offer is not None
                or state.pending_parallel_offer is not None or state.tool_repair_mode):
            return state
        feedback = self._vp_current_root_feedback()
        if feedback is None or not state.messages or state.messages[-1] == feedback:
            return state
        try:
            position = state.messages.index(feedback)
        except ValueError:
            return state
        messages = state.messages[:position] + state.messages[position + 1:] + [feedback]
        return replace(state, messages=messages)

    def _validation_progress_after_batch(self, state, calls, results):
        if self._vp_before is None:
            return False
        started = time.perf_counter()
        try:
            return self._validation_progress_observe_batch(state, calls, results)
        finally:
            self._vp_seconds += time.perf_counter() - started
            self.tracer.emit('validation_progress_guard_cost', scope_id=self.scope_id, step=state.step,
                             cumulative_guard_seconds=self._vp_seconds)

    def _validation_progress_observe_batch(self, state, calls, results):
        before = self._vp_before
        self._vp_before = None
        if before is None:
            return False
        files, certain = self._vp_snapshot()
        if not certain or not before[1]:
            return False
        was_active = before[2]
        source_changed=False
        validation_attempted=False
        if self._vp_active:
            current = digest([(p, files.get(p)) for p in self._vp_active['sources']])
            if current != self._vp_active.get('latest_version', self._vp_active['version']):
                source_changed=True
                self._recovery_change(state, 'revalidate', 'validation',
                                      self._vp_active['check'] + ':' + current)
                self._vp_active['latest_version'] = current
        for call, receipt in zip(calls, results):
            if any(receipt.get(k) for k in ('not_executed', '_semserve_reused', 'duplicate_in_same_turn')):
                continue
            explicit = call.name == 'finish_task' and 'public_check_passed' in receipt
            if call.name != 'shell' and not explicit:
                continue
            result = receipt.get('check', {}) if explicit else receipt
            output = result.get('output', '')
            command = 'python3 check.py' if explicit else call.arguments.get('command', '')
            invoked = self._vp_invoked_checks(command, files)
            frames = [self._vp_relative(p) for p in FRAME.findall(str(output))]
            candidates = [p for p in frames if p in invoked]
            passed = receipt.get('public_check_passed') is True if explicit else result.get('ok') is True and result.get('returncode') == 0
            if not candidates:
                # If an earlier producer in a failed && chain stopped, the
                # validator never executed. It cannot create failure evidence.
                candidates = invoked if passed or '&&' not in str(command) else []
            # Only the outer public validator owns the aggregate failure.
            for check in candidates[:1]:
                if self._vp_active and self._vp_active['check']==check:
                    validation_attempted=True
                if files.get(check) != (self._vp_initial or {}).get(check):
                    continue
                if passed:
                    self._vp_records.pop(check, None)
                    if self._vp_active and self._vp_active['check'] == check:
                        self.tracer.emit('validation_progress_resolved', scope_id=self.scope_id, step=state.step, check=check)
                        self._vp_active = None
                        self._recovery_change(state, 'resolve', 'validation')
                    continue
                if result.get('returncode') in (None, 0) or not output:
                    continue
                sources, complete = self._vp_sources(check, output, files)
                stable = complete and all(files.get(p) == before[0].get(p) for p in sources)
                if not stable:
                    continue  # Concurrent/source-changing checks cannot justify a stop.
                failure = digest(self._vp_diagnostic(output))
                version = digest([(p, files.get(p)) for p in sources])
                records = self._vp_records.setdefault(check, {})
                key = (failure, version)
                records[key] = records.get(key, 0) + 1
                if len(records) > 128:
                    records.pop(next(iter(records)))
                total = sum(n for (f, _), n in records.items() if f == failure)
                record = {'check': check, 'failure': failure, 'version': version,
                          'diagnostic': self._vp_diagnostic(output), 'sources': sources,
                          'repeat': records[key], 'remaining': RECOVERY_TURNS}
                self.tracer.emit('validation_progress_observed', scope_id=self.scope_id, step=state.step,
                                 check=check, failure_sha256=failure, source_version=version,
                                 repeat_count=records[key], same_failure_count=total,
                                 source_paths=sources, source_coverage='observed_traceback_and_static_import_closure')
                if self._vp_active and self._vp_active['check'] == check and self._vp_active['failure'] != failure:
                    self.tracer.emit('validation_progress_failure_changed', scope_id=self.scope_id, step=state.step, check=check)
                    # A different error is not a passing check. Keep the same
                    # bounded obligation instead of granting a fresh budget.
                    self._vp_active['failure'] = failure
                    self._vp_active['sources'] = sources
                    self._vp_active['latest_version'] = version
                    self._recovery_change(state, 'revalidate', 'validation', check + ':' + failure)
                if not self._vp_active and (records[key] >= REPEAT_LIMIT or total >= SAME_FAILURE_LIMIT):
                    episodes = self._vp_episodes.get(check, 0)
                    if episodes >= RECOVERY_EPISODES:
                        self._recovery_change(state, 'block', 'validation_recovery_episode_budget_exhausted')
                        self.tracer.emit('validation_progress_exhausted', scope_id=self.scope_id, step=state.step,
                                         check=check, reason='recovery_episode_budget_exhausted')
                        return True
                    self._vp_episodes[check] = episodes + 1
                    self._vp_active = record
                    self._recovery_change(state, 'begin', 'validation', check + ':' + failure, RECOVERY_TURNS,
                                          discard_reason='public_validation_recovery_required')
                    self._vp_feedback(state, record, output, files)
        if was_active and self._vp_active:
            # A repair on the last business batch must get one validation-only
            # dispatch. Do not refill its budget or allow another edit cycle.
            obligation=self._recovery.obligations.get('validation')
            if (source_changed and not validation_attempted and obligation is not None
                    and obligation.remaining==1 and not self._vp_active.get('final_recheck_used')):
                self._vp_active['final_recheck_used']=True
                self._vp_active['final_recheck_pending']=True
                state.messages.append({'role':'user','content':'[RUNTIME_FINAL_REVALIDATION] Relevant source changed at the recovery boundary. One validation-only opportunity remains: run the original check '+self._vp_active['check']+' with Python, or call finish_task to run it. Do not perform further inspection or edits. This does not reset recovery or accept the task without a passing check.'})
                self.tracer.emit('validation_final_recheck_reserved',scope_id=self.scope_id,step=state.step,
                    check=self._vp_active['check'],source_version=self._vp_active['latest_version'])
                return False
            self._vp_active['remaining'] = self._recovery_change(
                state, 'consume', 'validation', self._recovery_batch(state))
            self.tracer.emit('validation_progress_recovery_step', scope_id=self.scope_id, step=state.step,
                             check=self._vp_active['check'], remaining_business_batches=self._vp_active['remaining'])
            if self._vp_active['remaining'] <= 0:
                self.tracer.emit('validation_progress_exhausted', scope_id=self.scope_id, step=state.step,
                                 check=self._vp_active['check'], reason='six_business_batches_without_validation_improvement')
                return True
        return False

    def _validation_final_recheck_gate(self,state,call):
        active=getattr(self,'_vp_active',None)
        if not active or not active.get('final_recheck_pending'):
            return None
        if call.name in {'finish_task','report_frontier_state'}:
            return None
        if call.name=='shell':
            try:
                words=shlex.split(call.arguments.get('command',''))
                if len(words)>3 and words[0]=='cd' and words[2]=='&&' and Path(words[1]).resolve()==self._cross_workspace.root.resolve():words=words[3:]
                if len(words)==2 and Path(words[0]).name in {'python','python3','python3.12','python.exe'} and self._vp_relative(words[1])==active['check']:
                    return None
            except (ValueError,OSError):pass
        return {'ok':False,'not_executed':True,'completed':False,
            'status':'validation_only_recheck_required','check':active['check'],
            'error':'The final recovery opportunity is reserved for the original public check, not another inspection or edit. Run it with Python or call finish_task.'}
