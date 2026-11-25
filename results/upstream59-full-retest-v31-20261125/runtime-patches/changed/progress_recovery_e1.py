"""E1 problem-scoped progress recovery for the current Runtime."""
import ast
from dataclasses import dataclass, field
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import sys

from .progress_recovery import CONTROL, ProgressRecoveryMixin
from .recovery_state import business_evidence
from .validation_progress import FRAME, digest


TIMING_TASK = re.compile(r"\b(?:benchmark|profiling|latency|performance|timing)\b|性能|耗时|延迟|计时", re.I)
PYTHON = re.compile(r"python(?:\d+(?:\.\d+)?)?(?:\.exe)?$", re.I)
TIMED_CHECK = ast.parse(
    "import time; t=time.time(); import subprocess,sys; "
    "subprocess.run([sys.executable, 'CHECK']); print('elapsed', time.time()-t)"
)
TIMED_CHECK_DUMP = ast.dump(TIMED_CHECK)
VOLATILE_LINE = re.compile(r"(?im)^\s*(?:elapsed|elapsed_seconds|pid)\s*[:= ]\s*[0-9.eE+-]+\s*$")
LOOP_REPLAN_PROMPT = (
    'STOP. Runtime has detected a multi-turn reasoning and action loop. Reset your current approach. '
    'Re-derive the next step from the original task, the verified work already done, and the latest actual failure. '
    'Identify the next unmet requirement. Treat the repeated action and equivalent invocations as exhausted. '
    'In your next response, make one materially different tool call that changes the implementation '
    'or obtains evidence that can distinguish a concrete cause. If no such action is possible, '
    'use the available completion control to report the specific blocker.'
)
LOOP_SUMMARY = '[RUNTIME_E1_LOOP_SUMMARY]'
LOOP_RECEIPTS = frozenset({
    'duplicate_write_suppressed', 'duplicate_no_new_evidence', 'duplicate_tool_circuit_breaker',
    'progress_recovery_action_rejected', 'e1_problem_action_rejected',
})
SELFCHECK_SCRIPT = '.semserve/visible_checks/check.py'
SELFCHECK_MARKER = 'VISIBLE_CONTRACT_CHECK_JSON:'
DIAGNOSTIC_DIGEST = re.compile(r'(?i)\s*(?:digest\s*[:=]?\s+)?([0-9a-f]{64})\s*')
SELFCHECK_EVIDENCE = re.compile(r'\.semserve/visible_checks/evidence-[0-9a-f]{16}\.json')
SELFCHECK_LOG = re.compile(r'\.semserve/visible_checks/tool-output/[0-9a-f]{64}\.log')


def selfcheck_noop_rewrite(command):
    """Recognize a read/identity replace/write of the check script, with a literal debug print."""
    lines = command.strip().splitlines()
    if len(lines) < 3:
        return False
    header = re.fullmatch(r"(?:cd /workspace && )?python(?:\d+(?:\.\d+)?)? - <<\s*'([A-Za-z_]\w*)'", lines[0])
    if not header or lines[-1] != header[1]:
        return False
    try:
        tree = ast.parse('\n'.join(lines[1:-1]))
        path, source, change, *_ = tree.body
        target, value = path.targets[0].id, source.targets[0].id
        filename, old, new = path.value.value, *(node.value for node in change.value.args)
        if (filename not in {SELFCHECK_SCRIPT, '/workspace/' + SELFCHECK_SCRIPT}
                or not isinstance(old, str) or old != new or target == value
                or {target, value} & {'open', 'print'}):
            return False
        if len(tree.body) == 5:
            debug = tree.body[-1].value
            if not (isinstance(debug.func, ast.Name) and debug.func.id == 'print' and not debug.keywords
                    and all(isinstance(node, ast.Constant) for node in debug.args)):
                return False
            tree.body.pop()
        expected = ast.parse(f'{target}={filename!r}; {value}=open({target}).read(); '
                             f'{value}={value}.replace({old!r},{old!r}); open({target},"w").write({value})')
        return ast.dump(tree) == ast.dump(expected)
    except (AttributeError, IndexError, SyntaxError, TypeError, ValueError):
        return False


def selfcheck_evidence_view(command):
    """Recognize a plain or Python JSON view of one generated evidence artifact."""
    try:
        words = shlex.split(command)
        if words[:3] == ['cd', '/workspace', '&&']:
            words = words[3:]
        if len(words) == 2 and words[0] == 'cat':
            return words[1]
        if len(words) != 3 or not PYTHON.fullmatch(Path(words[0]).name) or words[1] != '-c':
            return None
        tree = ast.parse(words[2])
        imports, path, data, display = tree.body
        filename = path.value.value
        p, obj = path.targets[0].id, data.targets[0].id
        if not isinstance(filename, str) or p == obj or {p, obj} & {'json', 'open', 'print', 'list'}:
            return None
        expected = ast.parse(f'import json; {p}={filename!r}; {obj}=json.load(open({p}))')
        if any(ast.dump(a) != ast.dump(b) for a, b in zip((imports, path, data), expected.body)):
            return None
        fields = {'dumps', 'get', 'keys', 'items', 'values'}
        if (not isinstance(display, ast.Expr) or not isinstance(display.value, ast.Call)
                or not isinstance(display.value.func, ast.Name) or display.value.func.id != 'print'):
            return None
        for node in ast.walk(display):
            if isinstance(node, ast.Name) and node.id not in {'json', obj, 'print', 'list'}:
                return None
            if isinstance(node, ast.Attribute) and node.attr not in fields:
                return None
        return filename
    except (AttributeError, IndexError, SyntaxError, TypeError, ValueError):
        return None


def serial_check_command(command, sdk):
    """Recognize the serial runner at the end of a shell batch."""
    try:
        words = shlex.split(command.strip().splitlines()[-1])
    except (IndexError, ValueError):
        return False
    if words[:3] == ['cd', '/workspace', '&&']:
        words = words[3:]
    if words[-1:] == ['2>&1']:
        words.pop()
    if words[:4] == ['timeout', '--signal=TERM', '--kill-after=1s', '20s']:
        words = words[4:]
    if not words or not PYTHON.fullmatch(Path(words[0]).name):
        return False
    args = words[1:]
    if args[:1] == ['-B']:
        args.pop(0)
    return args in (['-m', 'unittest', 'discover', '-s', str(Path(SELFCHECK_SCRIPT).parent), '-p', 'check.py', '-v'],
                    [str(sdk), '--unittest'])


def serial_check_failures(result):
    failures = []
    if result.get('failure_index_complete') is True:
        for item in result.get('failure_index', []):
            location = item.get('test_location') or {}
            failures.append({**item, 'kind': item.get('kind') or item.get('phase'),
                             'line': location.get('line'),
                             'actual_failure': item.get('error', ''),
                             'diagnostic': item.get('error', '')})
        return failures
    for item in result.get('test_failures', []):
        trace = str(item.get('traceback', ''))
        lines = trace.strip().splitlines()
        frames = re.findall(r'File "[^"]*\.semserve/visible_checks/check\.py", line (\d+)', trace)
        failures.append(dict(test_id=item.get('test_id'), kind=item.get('kind'),
                             line=int(frames[-1]) if frames else None,
                             actual_failure=lines[-1][:400] if lines else '',
                             diagnostic=trace[-650:]))
    return failures


def canonical_selfcheck_tool(messages, result):
    """Find an already visible canonical receipt, never an external-only log."""
    for message in reversed(messages):
        if message.get('role') != 'tool':
            continue
        try:
            receipt = json.loads(message.get('content', ''))
        except (TypeError, ValueError):
            return None
        if not isinstance(receipt, dict):
            return None
        check = receipt.get('visible_contract_check')
        if not isinstance(check, dict):
            parent = receipt.get('check')
            check = parent.get('visible_contract_check') if isinstance(parent, dict) else None
        if isinstance(check, dict):
            if (check.get('script_sha256') == result.get('script_sha256')
                    and check.get('status') == result.get('status')):
                return message.get('tool_call_id') or 'structured_tool_result'
            return None
        if not receipt.get('truncated'):
            manual = manual_serial_result(str(receipt.get('output') or ''))
            if (manual is not None and manual.get('status') == result.get('status')
                    and manual.get('selfcheck_feedback') == result.get('selfcheck_feedback')
                    and manual.get('test_failures') == result.get('test_failures')):
                return message.get('tool_call_id') or 'manual_tool_result'
        return None
    return None


def manual_serial_result(output):
    tagged = [line[len(SELFCHECK_MARKER):] for line in output.splitlines()
              if line.startswith(SELFCHECK_MARKER)]
    if len(tagged) == 1:
        try:
            result = json.loads(tagged[0])
        except ValueError:
            return None
        if isinstance(result, dict) and result.get('test_framework') == 'unittest':
            return result
    if not re.search(r'(?m)^Ran \d+ tests? in ', output):
        return None
    sections = re.split(r'(?m)^(FAIL|ERROR): ([^\n]+)\n', output)
    failures = []
    for kind, name, trace in zip(sections[1::3], sections[2::3], sections[3::3]):
        _, sep, trace = trace.partition('-' * 70)
        if sep:
            trace = trace.split('=' * 70, 1)[0].split('-' * 70, 1)[0]
            failures.append(dict(test_id=name, kind=kind.lower(), traceback=trace))
    if failures:
        return {'status': 'FAILED', 'test_failures': failures}
    if re.search(r'(?m)^OK(?:\s|$)', output):
        return {'status': 'PASS_BOUNDED'}
    return None


def compact_e1_loop_history(messages):
    """Replace recent confirmed duplicate call/result pairs with one runtime note."""
    grouped = {}
    for index in range(max(0, len(messages) - 24), len(messages) - 1):
        call_msg, reply = messages[index:index + 2]
        calls = call_msg.get('tool_calls') or []
        if call_msg.get('role') != 'assistant' or len(calls) != 1 or reply.get('role') != 'tool':
            continue
        call = calls[0]
        if not call.get('id') or call['id'] != reply.get('tool_call_id'):
            continue
        function = call.get('function') or {}
        name = function.get('name')
        try:
            arguments = json.loads(function.get('arguments', ''))
            receipt = json.loads(reply.get('content', ''))
        except (TypeError, ValueError):
            continue
        if not name or not isinstance(arguments, dict) or not isinstance(receipt, dict):
            continue
        if receipt.get('status') not in LOOP_RECEIPTS or receipt.get('returncode') not in (None, 0):
            continue
        key = digest((name, arguments))
        target = arguments.get('path') or arguments.get('command') or ''
        row = grouped.setdefault(key, dict(tool=name, target=' '.join(str(target).split())[:220],
                                           pairs=[], statuses=set()))
        row['pairs'].append(index)
        row['statuses'].add(receipt['status'])
    removed, repeats = set(), []
    for row in grouped.values():
        if len(row['pairs']) < 2:
            continue
        for index in row['pairs']:
            removed.update((index, index + 1))
        repeats.append(dict(tool=row['tool'], target=row['target'], repeats=len(row['pairs']),
                            receipts=sorted(row['statuses']), outcome='No verified progress'))
    if not repeats:
        return 0
    messages[:] = [message for index, message in enumerate(messages) if index not in removed]
    messages.append({'role': 'user', 'content': LOOP_SUMMARY + '\n' +
                     json.dumps({'repeated_actions': repeats}, ensure_ascii=False)})
    return len(removed) // 2


@dataclass
class Problem:
    check: str
    diagnosis: str
    failed: bool
    signature: str
    sources: tuple[str, ...]
    version: str
    workspace_version: str
    streak: int = 0
    checks: set = field(default_factory=set)
    operations: dict = field(default_factory=dict)
    seen_versions: set = field(default_factory=set)
    diagnostic_facts: set[str] = field(default_factory=set)
    diagnostic_extension_used: bool = False


class E1ProgressRecoveryMixin(ProgressRecoveryMixin):
    def _progress_recovery_init(self):
        super()._progress_recovery_init()
        self._e1_problems = {}
        self._e1_active = None
        self._e1_before = None
        self._e1_last_failed_check = None
        self._e1_compact_loops = os.environ.get('SEMSERVE_E1_COMPACT_LOOPS') == '1'
        self._e1_selfcheck_phase = False
        self._e1_selfcheck_failure = None
        self._e1_selfcheck_digest = None
        self._e1_selfcheck_evidence = {}
        self._e1_selfcheck_inspected = set()
        self._e1_selfcheck_stall = None
        self._e1_selfcheck_observation = None
        self._e1_selfcheck_improved = False
        self._e1_selfcheck_new_diagnostic = False
        self._e1_selfcheck_diagnostic_versions = set()
        self._e1_selfcheck_diagnostic_recoveries = set()
        self._e1_selfcheck_receipt_ref = None
        self._e1_selfcheck_canonical_visible = False

    def _e1_enter_selfcheck(self, state):
        self._e1_selfcheck_phase = True
        self._e1_problems.clear()
        self._e1_active = self._e1_last_failed_check = None
        self._progress_recovery_clear(state, 'e1_public_pass_entered_serial_selfcheck')
        self._progress_recovery_seen.clear()
        self._progress_recovery_fingerprint, _ = self._progress_recovery_snapshot()

    def _e1_selfcheck_feedback(self, state, prefix):
        failure = self._e1_selfcheck_failure
        structured = (failure or {}).get('selfcheck_feedback')
        reference = {**(self._e1_selfcheck_receipt_ref or {}),
                     'script_sha256': failure['script_sha256'],
                     'candidate_version': failure['candidate_version']}
        # A truncated manual shell log may never have shown its parsed JSON to
        # the model. Publish one bounded canonical fallback in that case only.
        if not self._e1_selfcheck_canonical_visible:
            message = {**failure, 'check': SELFCHECK_SCRIPT, 'receipt_ref': reference}
            self._e1_selfcheck_canonical_visible = True
        else:
            message = {'check': SELFCHECK_SCRIPT, 'receipt_ref': reference,
                'test_ids': sorted({item.get('parent_test_id') or
                    str(item.get('test_id') or '').split(' (', 1)[0]
                    for item in failure.get('failures', [])}),
                'issue': {key: structured[key] for key in ('kind', 'code', 'target')
                          if structured and key in structured}}
        if prefix.endswith('_RECOVERY]'):
            action = ('The previous actions made no verified progress. Use the referenced failure index to '
                      'choose one targeted fixture or candidate edit, preserve the assertions, and execute '
                      'the suite. Repeating the same inspection or rewrite is not a repair.')
        elif prefix.endswith('_DIAGNOSTIC]'):
            action = ('The diagnostic opportunity is available. Apply one local edit justified by the '
                      'referenced failure and visible rule, then execute the suite; another unchanged '
                      'source slice or differently formatted receipt does not repair it.')
        else:
            action = ('Use the complete failure index in the canonical receipt. Distinguish a faulty '
                      'test input or expectation from candidate behavior before the next local edit.')
        message['recovery_action'] = action
        if self._e1_selfcheck_stall:
            message['stagnation_feedback'] = self._e1_selfcheck_stall
        if self._e1_selfcheck_digest:
            message['observed_diagnostic_digest'] = self._e1_selfcheck_digest
            message['recovery_action'] += (' This digest was already computed. Apply it to the fixture '
                                          'if relevant; recomputing the same digest is not progress.')
        message['step'] = state.step
        output = {'role': 'user', 'content': prefix + '\n' + json.dumps(message, ensure_ascii=False)}
        previous = state.messages[-1] if state.messages else {}
        if previous.get('role') == 'user' and str(previous.get('content', '')).startswith('[RUNTIME_E1_SELFCHECK_'):
            try:
                old = json.loads(previous['content'].split('\n', 1)[1])
            except (IndexError, TypeError, ValueError):
                old = {}
            # Coalesce the immediate acknowledgement and diagnostic reference,
            # but never replace the sole manual-log canonical fallback.
            if (old.get('step') == state.step and old.get('receipt_ref') == reference
                    and 'failures' not in old):
                state.messages[-1] = output
                return
        state.messages.append(output)

    @staticmethod
    def _e1_selfcheck_version(files):
        return digest(sorted((path, stamp) for path, stamp in files.items()
                             if not path.startswith('.semserve/')))

    def _e1_selfcheck_current(self):
        record = self._e1_selfcheck_failure
        if not record:
            return False
        files, certain = self._vp_snapshot()
        return (certain and files.get(SELFCHECK_SCRIPT) == record['script_sha256']
                and self._e1_selfcheck_version(files) == record['candidate_version'])

    def _e1_record_selfcheck(self, state, result, origin):
        files, certain = self._vp_snapshot()
        stamp = files.get(SELFCHECK_SCRIPT)
        if not certain or not stamp:
            return
        version = (stamp, self._e1_selfcheck_version(files))
        failures = serial_check_failures(result)
        tests = frozenset(result.get('test_ids') or ())
        if result.get('actual_case_count') != len(tests):
            tests = frozenset()
        test_hashes = {hashlib.sha256(str(test).encode()).hexdigest(): test for test in tests}
        failed = frozenset(test_hashes.get(item.get('parent_test_id_sha256')) or
            item.get('parent_test_id') or str(item.get('test_id') or '').split(' (', 1)[0]
            for item in failures)
        passed = tests - failed
        if (result.get('failed_cases') is not None
                and result.get('failed_cases') != len(failed)):
            passed = frozenset()  # A legacy preview cannot establish omitted passes.
        verified = frozenset((target, rule)
            for target, rules in (result.get('api_boundary_coverage', {}).get('verified') or {}).items()
            for rule in rules)
        observation = (version, result.get('status'), passed, verified)
        previous = self._e1_selfcheck_observation
        if previous is not None and previous[0] == version:
            self._e1_selfcheck_improved |= (
                (observation[1] == 'PASS_BOUNDED' and previous[1] != 'PASS_BOUNDED')
                or observation[2] > previous[2] or observation[3] > previous[3])
        self._e1_selfcheck_observation = observation
        if result.get('status') == 'PASS_BOUNDED':
            self._e1_selfcheck_failure = self._e1_selfcheck_digest = None
            return
        structured = result.get('selfcheck_feedback')
        if not isinstance(structured, dict):
            structured = None
        if not failures and not structured:
            return
        record = {'script_sha256': stamp, 'candidate_version': self._e1_selfcheck_version(files),
                  'failures': failures}
        if structured:
            record['selfcheck_feedback'] = structured
        evidence_path = result.get('evidence_path')
        if origin in {'finish_task', 'run_tests'} and isinstance(evidence_path, str) and SELFCHECK_EVIDENCE.fullmatch(evidence_path):
            self._e1_selfcheck_evidence[evidence_path] = digest(record)
        if self._e1_selfcheck_failure == record:
            return
        canonical = canonical_selfcheck_tool(state.messages, result)
        self._e1_selfcheck_canonical_visible = canonical is not None
        self._e1_selfcheck_receipt_ref = {'tool_call_id': canonical} if canonical else {}
        if isinstance(evidence_path, str):
            self._e1_selfcheck_receipt_ref['evidence_path'] = evidence_path
        self._e1_selfcheck_failure = record
        self._e1_selfcheck_new_diagnostic = True
        self._e1_selfcheck_digest = None
        self.tracer.emit('e1_selfcheck_failure_observed', scope_id=self.scope_id, step=state.step,
                         source=origin, **record)
        self._e1_selfcheck_feedback(state, '[RUNTIME_E1_SELFCHECK_FAILURE]')

    def _e1_observe_serial_shell(self, state, call, receipt):
        if call.name != 'shell' or any(receipt.get(k) for k in
                ('not_executed', '_semserve_reused', 'duplicate_no_new_evidence', 'duplicate_tool_circuit_breaker')):
            return
        output = str(receipt.get('output') or '')
        sdk = Path(__file__).resolve().parents[3] / 'visible_contract_check_sdk.py'
        if serial_check_command(call.arguments.get('command', ''), sdk):
            if receipt.get('truncated') and receipt.get('output_path'):
                full = self._cross_workspace.root / receipt['output_path']
                try:
                    if full.resolve().is_relative_to(self._cross_workspace.root / '.semserve/visible_checks/tool-output'):
                        raw = full.read_bytes()
                        if hashlib.sha256(raw).hexdigest() == receipt.get('output_sha256'):
                            output = raw.decode('utf8')
                except (OSError, ValueError):
                    pass
            result = manual_serial_result(output)
            if result is not None and (result.get('status') != 'PASS_BOUNDED' or receipt.get('returncode') == 0):
                self._e1_record_selfcheck(state, result, 'manual')
            return
        found = DIAGNOSTIC_DIGEST.fullmatch(output)
        if found and receipt.get('returncode') == 0 and not self._e1_selfcheck_digest and self._e1_selfcheck_current():
            self._e1_selfcheck_digest = found[1].lower()
            self._e1_selfcheck_feedback(state, '[RUNTIME_E1_SELFCHECK_DIAGNOSTIC]')

    def _progress_recovery_fact(self, call, result):
        fact = super()._progress_recovery_fact(call, result)
        record = self._e1_selfcheck_failure
        if fact and record and call.name == 'shell' and result.get('returncode') == 0:
            found = DIAGNOSTIC_DIGEST.fullmatch(str(result.get('output') or ''))
            if found and self._e1_selfcheck_current():
                return ('selfcheck_digest', record['script_sha256'], record['candidate_version'], found[1].lower())
        return fact

    def _progress_recovery_snapshot(self):
        if not self._e1_selfcheck_phase:
            return super()._progress_recovery_snapshot()
        files, certain = self._vp_snapshot()
        # Framework-generated receipts and output logs do not change the tested
        # implementation or script. Other workspace files still count normally.
        relevant = [(path, stamp) for path, stamp in files.items()
                    if not (SELFCHECK_EVIDENCE.fullmatch(path) or SELFCHECK_LOG.fullmatch(path))]
        return digest(sorted(relevant)), certain

    def _progress_recovery_operation_key(self, call):
        if (self._e1_selfcheck_phase and call.name == 'shell'
                and selfcheck_noop_rewrite(str(call.arguments.get('command') or ''))):
            return 'e1:selfcheck:identity-rewrite:' + SELFCHECK_SCRIPT
        return super()._progress_recovery_operation_key(call)

    def _e1_selfcheck_progress_receipt(self, call, receipt):
        if not receipt.get('ok') or receipt.get('not_executed'):
            return receipt
        command = str(call.arguments.get('command') or '')
        if call.name == 'shell' and receipt.get('returncode') == 0 and selfcheck_noop_rewrite(command):
            self._e1_selfcheck_stall = {
                'kind': 'stagnation', 'code': 'selfcheck_identity_rewrite', 'scope': self.scope_id,
                'target': SELFCHECK_SCRIPT, 'details': {'replacement_changes_content': False},
                'next_action': ('Make an edit that changes the failing test or the responsible implementation. '
                                'Replacing text with itself and printing a different debug message cannot repair it. '
                                'Then run the existing suite and call finish_task.'),
            }
        else:
            path = (call.arguments.get('path') if call.name == 'read_file' else
                    selfcheck_evidence_view(command) if call.name == 'shell' else None)
            if not path:
                return receipt
            signature = self._e1_selfcheck_evidence.get(self._vp_relative(path))
            if not signature:
                return receipt
            if signature not in self._e1_selfcheck_inspected:
                self._e1_selfcheck_inspected.add(signature)
                return receipt
            self._e1_selfcheck_stall = {
                'kind': 'stagnation', 'code': 'selfcheck_same_evidence', 'scope': self.scope_id,
                'target': SELFCHECK_SCRIPT, 'details': {'issue_sha256': signature},
                'next_action': ('Use the existing failure details to repair the cited declaration, test, or candidate. '
                                'Reading another receipt for the same issue does not perform a repair. '
                                'Call finish_task after the edit for an authoritative recheck.'),
            }
        # Preserve the raw tool reply. This copy is consumed only for E1's
        # evidence decision.
        return {**receipt, 'duplicate_no_new_evidence': True}

    def _progress_recovery_before_batch(self, state, calls):
        super()._progress_recovery_before_batch(state, calls)
        self._e1_before = None
        if self._progress_recovery_batch is not None:
            self._e1_before = self._vp_snapshot()

    def _e1_invocation(self, state, call):
        """Canonicalize only simple Python checks and the pure timing wrapper."""
        if call.name != 'shell':
            return None
        try:
            words = shlex.split(call.arguments.get('command', ''))
        except ValueError:
            return None
        if len(words) >= 4 and words[0] == 'cd' and words[2] == '&&':
            if self._vp_relative(words[1]) != '.':
                return None
            words = words[3:]
        if len(words) < 2 or not PYTHON.fullmatch(Path(words[0]).name):
            return None
        while len(words) > 1 and words[1] in {'-B', '-u'}:
            words.pop(1)
        if len(words) == 2 and words[1].endswith('.py'):
            check = self._vp_relative(words[1])
            return (check, 'direct') if check is not None else None
        if len(words) != 3 or words[1] != '-c' or TIMING_TASK.search(state.task):
            return None
        try:
            tree = ast.parse(words[2])
            invoke = tree.body[3].value
            target = invoke.args[0].elts[1]
            if not isinstance(target, ast.Constant) or not isinstance(target.value, str):
                return None
            path = target.value
            target.value = 'CHECK'
            if ast.dump(tree) != TIMED_CHECK_DUMP:
                return None
        except (AttributeError, IndexError, SyntaxError, TypeError, ValueError):
            return None
        check = self._vp_relative(path)
        return (check, 'timed') if check is not None else None

    def _e1_snapshot_version(self, problem, files):
        return digest([(p, files.get(p)) for p in problem.sources])

    def _e1_observe_check(self, state, call, receipt, before, files):
        if receipt.get('not_executed') or receipt.get('_semserve_reused'):
            return None
        explicit = call.name == 'finish_task' and 'public_check_passed' in receipt
        identity = ('check.py', 'direct') if explicit else self._e1_invocation(state, call)
        if identity is None:
            return None
        check, kind = identity
        if (check not in (self._vp_initial or {}) or files.get(check) != self._vp_initial[check]
                or not self._vp_parse(check, files)[0]):
            return None
        result = receipt.get('check', {}) if explicit else receipt
        output = str(result.get('output') or '')
        passed = receipt.get('public_check_passed') is True if explicit else result.get('returncode') == 0
        if kind == 'timed':
            # The wrapper does not propagate subprocess return codes. Accept
            # only the module's own success receipt and a clean process output.
            if not passed or 'Traceback' in output or not re.search(r'(?m)^MODULE_OK(?:\s|$)', output):
                return None
        elif not passed and (not output or result.get('returncode') in (None, 0)):
            return None
        paths, complete = self._vp_sources(check, output, files)
        if not complete:
            return None
        directory = Path(check).parent
        # Include colocated implementations and fixtures even when a test
        # imports the module dynamically and the assertion has no callee frame.
        paths = set(paths) | {p for p in files if Path(p).parent == directory
                              and Path(p).suffix in {'.py', '.json', '.toml', '.yaml', '.yml'}}
        if any(before.get(p) != files.get(p) for p in paths):
            return None
        diagnostic = self._vp_diagnostic(VOLATILE_LINE.sub('', output))
        frames = FRAME.findall(output)
        first_project_frames = [self._vp_relative(p) for p in frames]
        observed_locations = list(dict.fromkeys(p for p in first_project_frames if p in files))
        if observed_locations:
            diagnostic = 'Observed traceback files: ' + ', '.join(observed_locations[:8]) + '\n' + diagnostic
        return check, kind, not passed, diagnostic, tuple(sorted(paths))

    def _e1_relevant(self, problem, call):
        identity = self._tool_operation_key(call)
        if identity in problem.operations:
            return True
        path = call.arguments.get('path')
        if isinstance(path, str) and self._vp_relative(path) in problem.sources:
            return True
        command = call.arguments.get('command', '')
        return call.name == 'shell' and any(p in command or p.removesuffix('.py').replace('/', '.') in command
                                           for p in problem.sources if '/' in p)

    def _e1_diagnostic_fact(self, state, call, receipt, before, files):
        if not business_evidence(call.name, receipt):
            return None
        if call.name == 'read_file' and isinstance(call.arguments.get('path'), str):
            path = self._vp_relative(call.arguments['path'])
            stamp = files.get(path)
            if stamp and before.get(path) == stamp and receipt.get('content'):
                return digest(('source', path, stamp))
        if call.name == 'shell' and receipt.get('returncode') == 0 and self._e1_invocation(state, call) is None:
            output = VOLATILE_LINE.sub('', str(receipt.get('output') or ''))
            lines = [line.strip() for line in output.splitlines() if line.strip()]
            if lines:
                return digest(('probe', lines))
        return None

    def _e1_feedback(self, state, problem, remaining, new_diagnostic=False):
        message = {
            'replan_now': LOOP_REPLAN_PROMPT,
            'scope': self.scope_id, 'check': problem.check, 'failure_signature': problem.signature,
            'source_version': problem.version, 'failed': problem.failed,
            'last_actual_receipt': problem.diagnosis[-1800:], 'observed_source_paths': list(problem.sources[:16]),
            'business_batches_without_progress': problem.streak, 'recovery_business_batches_left': remaining,
            'action': (
                'Use the last failing assertion and its actual input to identify the responsible code path. '
                'Make a targeted content change, then rerun the original check on the new source. '
                'Inspect a relevant source or fixture once if needed. Repeating a diagnostic or an identical write is not a repair.'
                if problem.failed else
                'This module check already passed on the same source. Inspect the unresolved root check, '
                'its caller, or missing output. Continue toward the original task acceptance instead of timing the module again.'
            ),
            'completion': 'Preserve the original task and checker. If blocked, report the concrete unresolved evidence.',
        }
        if new_diagnostic:
            message['action'] = (
                'The last related diagnostic returned previously unseen evidence. Use the evidence and the '
                'most recent source already in the conversation to make a targeted edit to the implementation. '
                + ('This is the last recovery batch: make the edit in your next tool call. '
                   if remaining == 1 else 'If source is missing, one focused read can precede the edit. ')
                + 'After the edit, rerun the original check. A diagnostic consumes a batch and cannot earn another extension.'
            )
        self._e1_compact_history(state)
        state.messages.append({'role': 'user', 'content': '[RUNTIME_E1_PROBLEM_RECOVERY]\n' + json.dumps(message, ensure_ascii=False)})
        self.tracer.emit('e1_problem_recovery_requested', scope_id=self.scope_id, step=state.step,
                         check=problem.check, failure_signature=problem.signature, source_version=problem.version,
                         streak=problem.streak, remaining=remaining)

    def _progress_recovery_feedback(self, state, reason):
        """Add E1 direction when scope-level stalls have no matching check."""
        super()._progress_recovery_feedback(state, reason)
        if self._e1_selfcheck_phase:
            self._e1_compact_history(state)
            current = self._e1_selfcheck_current()
            if current:
                self._e1_selfcheck_feedback(state, '[RUNTIME_E1_SELFCHECK_RECOVERY]')
            elif self._e1_selfcheck_stall:
                state.messages.append({'role': 'user', 'content': '[RUNTIME_E1_SELFCHECK_RECOVERY]\n'
                    + json.dumps({'selfcheck_feedback': self._e1_selfcheck_stall}, ensure_ascii=False)})
            else:
                state.messages.append({'role': 'user', 'content': '[RUNTIME_E1_SELFCHECK_RECOVERY]\n'
                    'Call finish_task for the current authoritative self-check result. Use its receipt to select '
                    'the next edit to the self-check fixture or candidate and keep the existing tests.'})
            self.tracer.emit('e1_selfcheck_recovery_requested', scope_id=self.scope_id, step=state.step,
                             reason=reason, check=SELFCHECK_SCRIPT if current else None)
            return
        failure = self._e1_last_failed_check
        if failure is not None:
            files, certain = self._vp_snapshot()
            if not certain or any(files.get(p) != stamp for p, stamp in failure['source_stamps']):
                failure = None
        message = {'replan_now': LOOP_REPLAN_PROMPT, 'scope': self.scope_id, 'reason': reason}
        if failure is not None:
            message['last_failed_check'] = {k: v for k, v in failure.items() if k != 'source_stamps'}
            message['action'] = (
                'Use the last executed failure to select the next action. Work on the failing path shown in the '
                'traceback. Repair the responsible implementation or run a different probe that distinguishes '
                'a concrete cause. After a real change, rerun the original check.'
            )
        else:
            message['action'] = (
                'Use the original task and prior receipts to identify the next unmet requirement. '
                'Treat identical writes as already persisted. Implement the unfinished part or run the existing '
                'public check once when runnable to locate the next concrete blocker.'
            )
        self._e1_compact_history(state)
        state.messages.append({'role': 'user', 'content': '[RUNTIME_E1_SCOPE_RECOVERY]\n' + json.dumps(message, ensure_ascii=False)})
        self.tracer.emit('e1_scope_recovery_requested', scope_id=self.scope_id, step=state.step,
                         reason=reason, check=failure['check'] if failure else None)

    def _e1_compact_history(self, state):
        if self._e1_compact_loops:
            count = compact_e1_loop_history(state.messages)
            if count:
                self.tracer.emit('e1_loop_history_compacted', scope_id=self.scope_id,
                                 step=state.step, removed_tool_pairs=count)

    def _progress_recovery_preflight(self, state, call):
        problem = self._e1_active
        if problem is None:
            rejected = super()._progress_recovery_preflight(state, call)
            if (rejected and self._e1_selfcheck_phase and call.name == 'shell'
                    and selfcheck_noop_rewrite(str(call.arguments.get('command') or ''))):
                rejected['error'] = 'The shell command still replaces the self-check script text with itself.'
                if self._e1_selfcheck_stall:
                    rejected['selfcheck_feedback'] = self._e1_selfcheck_stall
            return rejected
        if call.name in CONTROL or call.name == 'finish_task':
            return None
        files, certain = self._vp_snapshot()
        if not certain or self._e1_snapshot_version(problem, files) != problem.version:
            return None
        key = self._tool_operation_key(call)
        invocation = self._e1_invocation(state, call)
        # Guard known equivalent checks and exact duplicate read/write actions.
        # Unfamiliar shell programs always execute.
        repeated_check = (invocation in problem.checks
                          and self._cross_workspace.fingerprint == problem.workspace_version)
        repeat_noop = problem.operations.get(key, 0) >= 2 and call.name in {'read_file', 'write_file', 'write_file_chunk', 'edit_file'}
        if not repeated_check and not repeat_noop:
            return None
        result = {'ok': False, 'not_executed': True, 'completed': False,
                  'status': 'e1_problem_action_rejected', 'check': problem.check,
                  'failure_signature': problem.signature, 'source_version': problem.version,
                  'error': 'This action already ran on the same evidence. Choose the targeted repair or a new diagnostic from the E1 feedback.'}
        self.tracer.emit('e1_problem_action_rejected', scope_id=self.scope_id, step=state.step,
                         call_id=call.id, tool=call.name, check=problem.check, executed=False)
        return result

    def _progress_recovery_after_batch(self, state, calls, results):
        if self._e1_selfcheck_phase:
            if self._progress_recovery_batch is None:
                return super()._progress_recovery_after_batch(state, calls, results)
            self._e1_selfcheck_stall = None
            normalized = []
            for call, result in zip(calls, results):
                self._e1_observe_serial_shell(state, call, result)
                normalized.append(self._e1_selfcheck_progress_receipt(call, result))
            fingerprint, certain = self._progress_recovery_snapshot()
            changed = certain and fingerprint != self._progress_recovery_batch['fingerprint']
            if changed or self._e1_selfcheck_improved:
                self._e1_selfcheck_improved = self._e1_selfcheck_new_diagnostic = False
                self._e1_selfcheck_diagnostic_recoveries.discard(fingerprint)
                self._progress_recovery_batch = None
                self._progress_recovery_fingerprint = fingerprint
                self._progress_recovery_clear(state, 'selfcheck_verified_edit_or_improvement')
                return False
            # New stdout/source slices are diagnosis, not repair of the pending
            # suite. Allow one diagnostic opportunity per unchanged issue;
            # do not reset an active recovery or refill its two-turn budget.
            diagnostic = self._e1_selfcheck_new_diagnostic or any(
                call.name in {'shell', 'read_file', 'search_text', 'list_files'}
                and business_evidence(call.name, result)
                and any(result.get(key) for key in ('output', 'content', 'matches', 'files'))
                for call, result in zip(calls, normalized))
            self._e1_selfcheck_new_diagnostic = False
            failure = self._e1_selfcheck_failure or {}
            feedback = failure.get('selfcheck_feedback') or {}
            issue = digest((fingerprint,
                [(item.get('test_id'), item.get('kind'), item.get('line'))
                 for item in failure.get('failures', [])],
                [feedback.get(key) for key in ('kind', 'code', 'scope', 'target')]))
            active_opportunity = (not self._progress_recovery_active
                or fingerprint not in self._e1_selfcheck_diagnostic_recoveries)
            if (certain and diagnostic and active_opportunity
                    and issue not in self._e1_selfcheck_diagnostic_versions):
                self._e1_selfcheck_diagnostic_versions.add(issue)
                if self._progress_recovery_active:
                    self._e1_selfcheck_diagnostic_recoveries.add(fingerprint)
                self._progress_recovery_batch = None
                self._e1_selfcheck_stall = {
                    'kind': 'diagnostic', 'code': 'selfcheck_diagnostic_only',
                    'scope': self.scope_id, 'target': SELFCHECK_SCRIPT,
                    'next_action': ('Use this evidence to create or repair the self-check fixture or candidate, '
                                    'then execute the suite. Another source slice or differently formatted '
                                    'receipt on unchanged files is not a repair.'),
                }
                if self._e1_selfcheck_current():
                    self._e1_selfcheck_feedback(state, '[RUNTIME_E1_SELFCHECK_DIAGNOSTIC]')
                else:
                    state.messages.append({'role': 'user', 'content': '[RUNTIME_E1_SELFCHECK_DIAGNOSTIC]\n'
                        + json.dumps({'selfcheck_feedback': self._e1_selfcheck_stall}, ensure_ascii=False)})
                self.tracer.emit('e1_selfcheck_diagnostic_opportunity', scope_id=self.scope_id,
                                 step=state.step, recovery_active=self._progress_recovery_active,
                                 recovery_attempts=self._progress_recovery_attempts)
                return False
            # Only the private progress view is normalized; preserve the actual
            # tool result and its failure details for the model and trace.
            normalized = [{**result, 'duplicate_no_new_evidence': True} for result in normalized]
            return super()._progress_recovery_after_batch(state, calls, normalized)
        if self._e1_before is None or not self._e1_before[1]:
            return super()._progress_recovery_after_batch(state, calls, results)
        before = self._e1_before[0]
        self._e1_before = None
        files, certain = self._vp_snapshot()
        if not certain:
            return super()._progress_recovery_after_batch(state, calls, results)
        active = self._e1_active
        repair_evidence = None
        touched = set()
        new_evidence = set()
        for call, receipt in zip(calls, results):
            observed = self._e1_observe_check(state, call, receipt, before, files)
            if observed is None:
                continue
            check, kind, failed, diagnosis, paths = observed
            if failed:
                self._e1_last_failed_check = {
                    'check': check, 'diagnosis': diagnosis[-1800:], 'observed_step': state.step,
                    'source_stamps': [(path, files.get(path)) for path in paths],
                }
            elif check == 'check.py' or (self._e1_last_failed_check and check == self._e1_last_failed_check['check']):
                self._e1_last_failed_check = None
            if check == 'check.py' and active is not None and not active.failed:
                # A real root validation replaces the already-passing module
                # as the recovery objective, even if the root check fails.
                self._e1_problems.pop(active.check, None)
                self._e1_active = None
                self._progress_recovery_clear(state, 'e1_root_validation_observed')
                self.tracer.emit('e1_problem_advanced', scope_id=self.scope_id, step=state.step,
                                 check=active.check, next_check=check, next_check_passed=not failed)
                active = None
            problem = self._e1_problems.get(check)
            if not failed and problem and problem.failed:
                self._e1_problems.pop(check)
                if problem is active:
                    self._e1_active = None
                    self._progress_recovery_clear(state, 'e1_original_check_passed')
                    active = None
                self.tracer.emit('e1_problem_resolved', scope_id=self.scope_id, step=state.step, check=check)
                continue
            if not failed and check == 'check.py':
                continue
            signature = digest((failed, diagnosis))
            version = digest([(p, files.get(p)) for p in paths])
            if problem is None or (problem.signature, problem.version) != (signature, version):
                if problem is active and active is not None:
                    # A changed diagnostic alone does not refill active recovery.
                    problem.signature, problem.diagnosis, problem.failed = signature, diagnosis, failed
                    problem.sources, problem.version = paths, version
                    problem.operations.clear()
                    problem.checks.clear()
                else:
                    previous_versions = problem.seen_versions.copy() if problem else set()
                    problem = Problem(check, diagnosis, failed, signature, paths, version,
                                      self._cross_workspace.fingerprint, seen_versions=previous_versions)
                    self._e1_problems[check] = problem
                    new_evidence.add(check)
            problem.seen_versions.add(version)
            problem.checks.add((check, kind))
            problem.workspace_version = self._cross_workspace.fingerprint
            touched.add(check)
        for check, problem in list(self._e1_problems.items()):
            version = self._e1_snapshot_version(problem, files)
            if version != problem.version:
                novel = version not in problem.seen_versions
                problem.seen_versions.add(version)
                problem.version = version
                problem.checks.clear()
                problem.operations.clear()
                if novel:
                    new_evidence.add(check)
                    problem.streak = 0
                    problem.diagnostic_facts.clear()
                    problem.diagnostic_extension_used = False
                    if self._e1_active is problem:
                        self._e1_active = None
                        self._progress_recovery_clear(state, 'e1_related_source_changed')
                        self.tracer.emit('e1_problem_revalidation_allowed', scope_id=self.scope_id, step=state.step, check=check)
            related = [(c, r) for c, r in zip(calls, results) if c.name not in CONTROL and self._e1_relevant(problem, c)]
            if related or check in touched:
                touched.add(check)
            if check not in touched or check in new_evidence:
                continue
            for call, receipt in related:
                key = self._tool_operation_key(call)
                fact = self._e1_diagnostic_fact(state, call, receipt, before, files) if problem.failed else None
                if fact is not None and fact not in problem.diagnostic_facts and len(problem.diagnostic_facts) < 128:
                    problem.diagnostic_facts.add(fact)
                    if (problem is active and not problem.diagnostic_extension_used
                            and key not in problem.operations):
                        repair_evidence = fact
                problem.operations[key] = problem.operations.get(key, 0) + 1
                if len(problem.operations) > 64:
                    problem.operations.pop(next(iter(problem.operations)))
            if problem is active and repair_evidence is not None:
                continue
            problem.streak += 1
            self.tracer.emit('e1_problem_stalled', scope_id=self.scope_id, step=state.step, check=check,
                             failure_signature=problem.signature, source_version=problem.version, streak=problem.streak)
        if len(self._e1_problems) > 12:
            for check, problem in list(self._e1_problems.items()):
                if problem is not self._e1_active and check not in touched:
                    self._e1_problems.pop(check)
                    break
        if active is not None and self._e1_active is active:
            if repair_evidence is not None:
                active.diagnostic_extension_used = True
                remaining = self._recovery.obligations['tool_progress'].remaining
                self.tracer.emit('e1_problem_diagnostic_extension', scope_id=self.scope_id,
                                 step=state.step, check=active.check,
                                 source_version=active.version, evidence_sha256=repair_evidence,
                                 remaining=remaining)
                self._e1_feedback(state, active, remaining, new_diagnostic=True)
                return False
            if any(c.name not in CONTROL for c in calls):
                remaining = self._recovery_change(state, 'consume', 'tool_progress', self._recovery_batch(state))
                self._progress_recovery_attempts = 2 - remaining
                if remaining <= 0:
                    self.tracer.emit('e1_problem_recovery_exhausted', scope_id=self.scope_id, step=state.step, check=active.check)
                    return True
                self._e1_feedback(state, active, remaining)
            return False
        eligible = [p for p in self._e1_problems.values() if p.check in touched and p.streak >= 3]
        if eligible and not self._progress_recovery_active:
            problem = max(eligible, key=lambda p: (p.failed, p.streak))
            self._e1_active = problem
            self._progress_recovery_active = True
            self._progress_recovery_attempts = 0
            self._recovery_change(state, 'begin', 'tool_progress', problem.check + ':' + problem.signature, 2,
                                  discard_reason='e1_problem_recovery_required')
            self._e1_feedback(state, problem, 2)
            return False
        if touched and not self._progress_recovery_active:
            self._progress_recovery_batch = None
            self._progress_recovery_streak = 0
            self._progress_recovery_fingerprint = self._cross_workspace.fingerprint
            return False
        return super()._progress_recovery_after_batch(state, calls, results)


def install_e1():
    """Select E1 before importing AgentRuntime, including its child runtimes."""
    if 'agent_runtime_demo.runtime' in sys.modules:
        raise RuntimeError('Select E1 before importing AgentRuntime')
    from . import progress_recovery
    progress_recovery.ProgressRecoveryMixin = E1ProgressRecoveryMixin

