"""Runtime-owned test receipts for file branches, never model-declared passes."""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shlex
import shutil
import subprocess
import tempfile
import time
import uuid


def branch_selfcheck_enabled():
    return os.getenv('SEMSERVE_BRANCH_ENTRY_SELFCHECK') == '1'


def component_entries(root, paths):
    """Find the standard component CLI using the owned files and local output contract."""
    paths = set(paths)
    entries = []
    for name in sorted(paths):
        if PurePosixPath(name).name != 'render.py':
            continue
        contract = PurePosixPath(name).with_name('contract.json').as_posix()
        path = checked_path(root, contract)
        if not path.is_file():
            continue
        data = json.loads(path.read_text(encoding='utf8'))
        output = data.get('output') if isinstance(data, dict) else None
        if isinstance(output, str) and output.endswith('.json') and output in paths:
            entries.append((name, contract, output))
    return entries


def checked_path(root, name):
    if (not isinstance(name, str) or not name or '\\' in name or ':' in name
            or name.startswith('/') or any(p in ('', '.', '..') for p in name.split('/'))):
        raise ValueError('Expected a normalized workspace-relative file path: ' + repr(name))
    path = root / name
    if (not path.resolve().is_relative_to(root) or path.is_symlink()
            or path.resolve().relative_to(root).as_posix() != name):
        raise ValueError('Check path escapes workspace or is a symlink: ' + name)
    return path


def source_versions(root, paths):
    result = {}
    for name in sorted(set(paths)):
        path = checked_path(root, name)
        result[name] = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
    return result


class FileBranchChecks:
    def __init__(self, root, branch_id, attempt_id):
        self.root = Path(root).resolve()
        self.branch_id = branch_id
        self.attempt_id = attempt_id
        self.cache = {}
        self.attested = set()
        self.scope = None

    def tracked_paths(self, paths, targets, inputs):
        tracked = set(paths) | set(targets)
        contracts = [inputs.get(k) or {} for k in ('_runtime_implementation_contract', '_runtime_frontier_contract')]
        g1 = os.getenv('SEMSERVE_G1') == '1'
        infer_contract_inputs = not g1
        if g1:
            from .g1_discovery import contract_heuristics_enabled
            infer_contract_inputs = contract_heuristics_enabled()
        for contract in contracts:
            tracked.update(contract.get('read_set') or [])
            if g1 and not infer_contract_inputs:
                tracked.update(contract.get('validation_read_set') or [])
        # Check implementations and their visible local contracts/fixtures are
        # part of the receipt. Unrelated siblings do not invalidate the receipt.
        folders = {str(PurePosixPath(p).parent) for p in set(paths) | set(targets)
                   if PurePosixPath(p).suffix == '.py'}
        for folder in folders:
            directory = self.root / folder
            if directory.is_dir():
                for p in directory.iterdir():
                    if p.is_file() and p.suffix.lower() in ('.py', '.json', '.md', '.toml'):
                        tracked.add(p.relative_to(self.root).as_posix())
            local_contract = directory / 'contract.json'
            if infer_contract_inputs and local_contract.is_file():
                contract = json.loads(local_contract.read_text(encoding='utf8'))
                for key in ('input', 'inputs'):
                    value = contract.get(key)
                    if isinstance(value, str):
                        tracked.add(value)
                    elif isinstance(value, list):
                        tracked.update(value)
        if (self.root / 'README.md').is_file():
            tracked.add('README.md')
        return tracked

    def complete(self, result, *, call_id, paths, targets, inputs, execute, emit, check_entries=False):
        from .g1_branch_checks import complete_g1
        g1_result = complete_g1(self, result, call_id=call_id, paths=paths, targets=targets,
                                inputs=inputs, execute=execute, emit=emit)
        if g1_result is not None:
            return g1_result
        result = copy.deepcopy(result)
        if result.get('ok') is not True:
            return result
        missing = sorted(set(paths) - set(result.get('files', {})))
        if missing:
            return dict(result, ok=False, completion_accepted=False,
                        error='branch_delivery_incomplete', missing_artifact_paths=missing,
                        next_action='Deliver every assigned file; file reads alone do not complete the branch.')
        try:
            for target in targets:
                path = checked_path(self.root, target)
                if path.suffix != '.py' or not path.is_file():
                    raise ValueError('required_test_targets must name existing executable Python check files: ' + target)
            tracked = self.tracked_paths(paths, targets, inputs)
            versions = source_versions(self.root, tracked)
            self.scope = (tuple(paths), tuple(targets), copy.deepcopy(inputs))
            entries = component_entries(self.root, paths) if check_entries else []
        except (ValueError, OSError, TypeError) as exc:
            return dict(result, ok=False, completion_accepted=False,
                        error='branch_test_target_invalid', details=str(exc), missing_test_targets=list(targets),
                        next_action='Inspect the declared check path and its prerequisites. Tests are not waived; repair the check invocation or report the invalid branch contract to the parent.')
        if not targets and not entries:
            return result
        receipts = []
        entry_targets = []
        for entry, contract, output in entries:
            target = f'entry:{entry} -> {output}'
            expected = result['sha256'][output]
            key = json.dumps([self.branch_id, self.attempt_id, target, versions, expected], sort_keys=True)
            proof = copy.deepcopy(self.cache.get(key))
            if proof is None:
                started = time.time()
                try:
                    check = self._execute_component_entry(entry, contract, output, expected, versions, execute)
                    after = source_versions(self.root, self.tracked_paths(paths, targets, inputs))
                    proof = dict(check, passed=check['passed'] and versions == after,
                                 source_version_matches=versions == after)
                except (ValueError, OSError) as exc:
                    proof = dict(passed=False, error=str(exc))
                proof.update(target=target, entrypoint=entry, output_path=output,
                             branch_id=self.branch_id, attempt_id=self.attempt_id,
                             seconds=time.time()-started, reused=False)
                if proof['passed']:
                    self.cache[key] = copy.deepcopy(proof)
            else:
                proof['reused'] = True
            emit('branch_entry_selfcheck_completed', tool_call_id=call_id, **proof)
            receipts.append(proof)
            if not proof['passed']:
                return dict(result, ok=False, completion_accepted=False,
                            error='branch_entry_selfcheck_failed', runtime_focused_checks=receipts,
                            next_action=(f'Repair {entry} so executing it as a script regenerates {output} '
                                         'from the declared inputs with no existing output. '
                                         'Use the real check result and deliver again after repair.'))
            entry_targets.append(target)
        for target in targets:
            key = json.dumps([self.branch_id, self.attempt_id, target, versions], sort_keys=True)
            proof = copy.deepcopy(self.cache.get(key))
            if proof is None:
                # Keep commands inside the existing shell workspace policy;
                # absolute interpreter paths are intentionally rejected there.
                # A fresh, unwritten cache prefix also avoids timestamp/size
                # based stale .pyc reuse after a same-second local repair.
                args = ['python' if os.name == 'nt' else 'python3', '-B', '-X',
                        'pycache_prefix=.semserve/check-pycache-' + uuid.uuid4().hex, target]
                command = subprocess.list2cmdline(args) if os.name == 'nt' else shlex.join(args)
                start = time.time()
                check = execute(command)
                after = source_versions(self.root, self.tracked_paths(paths, targets, inputs))
                passed = (check.get('ok') is True and check.get('returncode') == 0 and versions == after)
                proof = dict(target=target, command=command, passed=passed,
                             returncode=check.get('returncode'), output=check.get('output', ''),
                             error=check.get('error'), source_sha256=after, source_version_matches=versions == after,
                             branch_id=self.branch_id, attempt_id=self.attempt_id,
                             seconds=time.time()-start, reused=False)
                if passed:
                    self.cache[key] = copy.deepcopy(proof)
            else:
                proof['reused'] = True
            emit('branch_focused_check_completed', tool_call_id=call_id, **proof)
            receipts.append(proof)
            if not proof['passed']:
                return dict(result, ok=False, completion_accepted=False,
                            error='branch_focused_check_failed', runtime_focused_checks=receipts,
                            missing_test_targets=[target],
                            next_action='Use the real check output/traceback to repair the assigned implementation or its prerequisites. Deliver again after repair; repeated unchanged delivery is not progress.')
        result.update(tested_targets=list(targets) + entry_targets, tests_passed=True,
                      verification_scope='file_integrity_and_runtime_checks',
                      runtime_focused_checks=receipts, runtime_test_source_sha256=versions,
                      completion_accepted=True)
        token = hashlib.sha256(json.dumps([call_id, result['sha256'], receipts], sort_keys=True).encode()).hexdigest()
        result['runtime_test_receipt_id'] = token
        self.attested.add(token)
        return result

    def _execute_component_entry(self, entry, contract, output, expected, versions, execute):
        # Only the scoped files and declared inputs are copied. A pre-existing
        # delivered output must never satisfy a fresh regeneration check.
        with tempfile.TemporaryDirectory(prefix='semserve-branch-entry-') as directory:
            sandbox = Path(directory)
            for name, version in versions.items():
                if version is None or name == output:
                    continue
                target = sandbox / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(checked_path(self.root, name), target)
                if hashlib.sha256(target.read_bytes()).hexdigest() != version:
                    raise ValueError('A scoped input changed before branch self-check: ' + name)
            generated = checked_path(sandbox, output)
            generated.parent.mkdir(parents=True, exist_ok=True)
            command = 'cd ' + shlex.quote(directory) + ' && ' + shlex.join(
                ['python3', '-B', entry, directory, contract])
            check = execute(command)
            produced = generated.is_file() and not generated.is_symlink()
            actual = hashlib.sha256(generated.read_bytes()).hexdigest() if produced else None
            passed = check.get('ok') is True and check.get('returncode') == 0 and actual == expected
            error = check.get('error')
            if check.get('returncode') == 0 and actual != expected:
                error = 'Script exited 0 without creating the required output' if actual is None else (
                    'Regenerated output SHA256 differs from the delivered file')
            return dict(passed=passed, returncode=check.get('returncode'),
                        output=str(check.get('output') or '')[-2400:], error=error,
                        expected_output_sha256=expected, actual_output_sha256=actual)

    def artifact_fields(self, result):
        if result.get('runtime_test_receipt_id') not in self.attested:
            return {}
        fields = {k: copy.deepcopy(result[k]) for k in
                ('tested_targets', 'tests_passed', 'verification_scope', 'runtime_focused_checks',
                 'runtime_test_source_sha256', 'runtime_test_receipt_id')}
        for key in ('real_input_validation', 'missing_validation_inputs', 'runtime_validation_input_sha256'):
            if key in result:
                fields[key] = copy.deepcopy(result[key])
        return fields

    def still_current(self, artifact):
        versions = artifact.get('runtime_test_source_sha256')
        if not isinstance(versions, dict):
            return False
        try:
            if self.scope is None:
                return False
            paths, targets, inputs = self.scope
            tracked = self.tracked_paths(paths, targets, inputs)
            if str(artifact.get('verification_scope', '')).startswith('g1_'):
                from .g1_branch_checks import freshness_paths
                tracked = freshness_paths(self, paths, targets, inputs,
                                          real_input_validated=artifact.get('real_input_validation') == 'passed')
            return versions == source_versions(self.root, tracked)
        except (OSError, ValueError):
            return False
