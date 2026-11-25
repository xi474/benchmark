"""G1 private file-branch checks and Linux write isolation.

The model still uses the ordinary shell schema. A Runtime-owned launcher applies
Landlock before executing its command, and only CAS-checked owned changes can be
exported. A changed cwd is not used as the isolation boundary.
"""
from __future__ import annotations

import ast
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import uuid

TEST_PATH = ".semserve/g1_checks/test_branch.py"
MARKER = "G1_BRANCH_CHECK_JSON:"
_MIRRORS = {}
_LOCK = threading.RLock()


def enabled():
    return os.getenv("SEMSERVE_G1") == "1"


def _digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def _safe(root, name):
    if not isinstance(name, str) or not name or "\\" in name or ":" in name:
        raise ValueError("Expected a workspace-relative path")
    if name.startswith("/") or any(p in ("", ".", "..") for p in name.split("/")):
        raise ValueError("Unsafe branch path: " + name)
    path = root / name
    if not path.resolve().is_relative_to(root.resolve()) or path.is_symlink():
        raise ValueError("Branch path escapes workspace: " + name)
    return path


def _tree(root):
    return {p.relative_to(root).as_posix(): _digest(p) for p in root.rglob("*")
            if p.is_file() and not p.is_symlink()
            and ".semserve" not in p.relative_to(root).parts
            and "__pycache__" not in p.relative_to(root).parts}


def _policy_error(command):
    """Preserve the existing shell's model-command policy before wrapping it."""
    if not isinstance(command, str) or not command.strip():
        return "command must be a non-empty string"
    text = command.lower()
    patterns = (r"\.\.[\\/]", r"(?<![a-z0-9_])[a-z]:[\\/]",
                r"(?:turns|trace|api_events|wire_requests|execution_state)\.jsonl",
                r"get-childitem\s+env", r"\$env:", r"os\.environ")
    if any(re.search(pattern, text) for pattern in patterns):
        return "shell command rejected: access is restricted to the task workspace"
    if re.search(r"(?:^|[;&|]\s*)nohup\s+", text):
        return "detached background processes are outside the Runtime lifecycle"
    if (("/proc" in text and re.search(r"\bkill\b", text))
            or re.search(r"\bpkill\s+(?:-[a-z]*f[a-z]*|--full)\b", text)
            or re.search(r"\bkillall\b", text)):
        return "broad process-name kills are not allowed"
    if (os.getenv("AGENT_RUNTIME_FORBID_BROWSER_INSTALL", "").lower() in {"1", "true", "yes"}
            and re.search(r"(?:playwright\s+install|npm\s+(?:install|i|add)[^\n;]*playwright|npx\s+playwright\s+install)", text)):
        return "browser installation is provided by the separate verifier"
    return None


def landlock_abi():
    if sys.platform != "linux":
        return 0
    import ctypes
    libc = ctypes.CDLL(None, use_errno=True)
    result = libc.syscall(444, 0, 0, 1)
    return max(0, result)


def _restrict_writes(directory):
    import ctypes
    libc = ctypes.CDLL(None, use_errno=True)
    abi = libc.syscall(444, 0, 0, 1)
    if abi < 3:
        raise RuntimeError("G1 requires Landlock ABI >= 3; writes remain blocked")
    rights = sum(1 << bit for bit in (1, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14))

    class Ruleset(ctypes.Structure):
        _fields_ = [("handled_access_fs", ctypes.c_uint64)]

    class Beneath(ctypes.Structure):
        _pack_ = 1
        _fields_ = [("allowed_access", ctypes.c_uint64), ("parent_fd", ctypes.c_int32)]

    ruleset = Ruleset(rights)
    fd = libc.syscall(444, ctypes.byref(ruleset), ctypes.sizeof(ruleset), 0)
    if fd < 0:
        raise OSError(ctypes.get_errno(), "landlock_create_ruleset")
    try:
        for path, access in ((directory, rights), ("/dev/null", 1 << 1)):
            parent = os.open(path, os.O_PATH | os.O_CLOEXEC)
            try:
                rule = Beneath(access, parent)
                if libc.syscall(445, fd, 1, ctypes.byref(rule), 0) != 0:
                    raise OSError(ctypes.get_errno(), "landlock_add_rule")
            finally:
                os.close(parent)
        if libc.prctl(38, 1, 0, 0, 0) != 0:
            raise OSError(ctypes.get_errno(), "PR_SET_NO_NEW_PRIVS")
        if libc.syscall(446, fd, 0) != 0:
            raise OSError(ctypes.get_errno(), "landlock_restrict_self")
    finally:
        os.close(fd)


def _launcher(directory, packet_path):
    packet = json.loads(Path(packet_path).read_text(encoding="utf-8"))
    _restrict_writes(directory)
    os.chdir(directory)
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    os.environ["TMPDIR"] = str(Path(directory) / ".semserve/g1_checks/tmp")
    Path(os.environ["TMPDIR"]).mkdir(parents=True, exist_ok=True)
    os.execv("/bin/sh", ["/bin/sh", "-c", packet["command"]])


class BranchMirror:
    def __init__(self, root, branch_id, attempt_id):
        self.root = Path(root).resolve()
        self.path = Path(tempfile.mkdtemp(prefix="semserve-g1-branch-"))
        self.branch_id, self.attempt_id = branch_id, attempt_id
        self.lock = threading.RLock()
        self.owned = set()
        self.inputs = {}
        self.root_versions = {}

    def sync(self):
        current = _tree(self.root)
        for name, digest in current.items():
            owned_source_changed = self._is_owned(name) and name.endswith(".py") and _digest(self.path/name) != digest
            if self.root_versions.get(name) != digest or not (self.path / name).exists() or owned_source_changed:
                target = _safe(self.path, name)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(_safe(self.root, name), target)
        for name in self.root_versions.keys() - current.keys():
            target = _safe(self.path, name)
            if target.is_file() and _digest(target) == self.root_versions[name]:
                target.unlink()
        self.root_versions = current

    def _is_owned(self, name):
        return name in self.owned or any(name.startswith(p.rstrip("/") + "/") for p in self.owned)

    def _validation_inputs(self):
        paths = set()
        for key in ("_runtime_implementation_contract", "_runtime_frontier_contract"):
            contract = self.inputs.get(key) or {}
            paths.update(contract.get("validation_read_set") or [])
        from .g1_discovery import contract_heuristics_enabled
        if not contract_heuristics_enabled():
            return paths
        for name in self.owned:
            if not name.endswith(".py"):
                continue
            contract_path = self.root / Path(name).parent / "contract.json"
            if contract_path.is_file():
                data = json.loads(contract_path.read_text(encoding="utf-8"))
                paths.update(data.get("inputs") or [])
        return paths

    def run(self, command, *, context=None, timeout=30, max_output_chars=20000, export=True, refresh=True):
        error = _policy_error(command)
        if error:
            return dict(ok=False, returncode=-2, output="", error=error, status="g1_command_policy_rejected")
        if landlock_abi() < 3:
            return dict(ok=False, returncode=-8, output="", status="g1_isolation_unavailable",
                        error="Linux Landlock ABI >= 3 is required; command not executed", not_executed=True)
        from .tools.shell import ShellTool
        with self.lock:
            if refresh:
                self.sync()
            before = _tree(self.path)
            root_before = dict(self.root_versions)
            effective = command.replace(str(self.root), str(self.path))
            if Path("/app").exists() and Path("/app").resolve() == self.root:
                effective = effective.replace("/app/", str(self.path) + "/")
                effective = re.sub(r"(?<!\w)/app(?=[\s'\"]|$)", str(self.path), effective)
            packet = self.path / ".semserve/g1_checks" / ("command-" + uuid.uuid4().hex + ".json")
            packet.parent.mkdir(parents=True, exist_ok=True)
            packet.write_text(json.dumps({"command": effective}), encoding="utf-8")
            wrapped = shlex.join([sys.executable, "-B", "-P", str(Path(__file__).resolve()),
                                  "_landlock", str(self.path), str(packet)])
            tool = ShellTool(self.path, timeout_seconds=timeout, max_output_chars=max_output_chars)
            result = tool.execute_with_context({"command": wrapped}, context)
            after = _tree(self.path)
            changed = sorted(name for name in before.keys() | after.keys() if before.get(name) != after.get(name))
            validation_inputs = self._validation_inputs()
            pending = [name for name in validation_inputs
                       if not (self.root / name).is_file()
                       or _digest(self.path / name) != _digest(self.root / name)]
            committed, not_committed, conflicts = [], [], []
            for name in changed:
                if not export or not self._is_owned(name) or (pending and name.endswith(".json")):
                    not_committed.append(name)
                    continue
                target = _safe(self.root, name)
                if _digest(target) != root_before.get(name):
                    conflicts.append(name)
                    continue
                source = _safe(self.path, name)
                if source.is_file():
                    target.parent.mkdir(parents=True, exist_ok=True)
                    temporary = target.with_name(target.name + ".g1-" + uuid.uuid4().hex)
                    temporary.write_bytes(source.read_bytes())
                    os.replace(temporary, target)
                elif target.is_file():
                    target.unlink()
                committed.append(name)
            self.root_versions = _tree(self.root)
            result.update(g1_isolation="landlock_private_workspace", execution_workspace=str(self.path),
                          committed_owned_paths=committed, not_committed_paths=not_committed,
                          real_input_validation="pending" if pending else "not_yet_checked",
                          missing_or_fixture_inputs=sorted(pending), source_conflicts=conflicts)
            if conflicts:
                result.update(ok=False, status="g1_source_version_conflict", error="Owned source changed before commit: " + ", ".join(conflicts))
            return result


def _mirror(root, branch_id, attempt_id):
    key = (str(Path(root).resolve()), str(branch_id), str(attempt_id))
    with _LOCK:
        if key not in _MIRRORS:
            _MIRRORS[key] = BranchMirror(root, branch_id, attempt_id)
        return _MIRRORS[key]


def freshness_paths(checks, paths, targets, inputs, *, real_input_validated=False):
    """A future validation artifact is not an input to an isolated code check.

    Explicit coding reads remain binding even if repeated in validation reads.
    Real-input checks always retain the full dependency/version scope.
    """
    tracked = checks.tracked_paths(paths, targets, inputs)
    contract = {}
    for key in ("_runtime_implementation_contract", "_runtime_frontier_contract"):
        contract.update(inputs.get(key) or {})
    if enabled() and contract.get("validation_mode") == "isolated_fixture" and not real_input_validated:
        validation_only = set(contract.get("validation_read_set") or []) - set(contract.get("read_set") or [])
        tracked.difference_update(validation_only)
    return tracked


def maybe_execute_branch_shell(runtime, call, context):
    if (not enabled() or call.name != "shell" or runtime.depth <= 0
            or runtime.required_artifact_kinds != ("file",)):
        return None
    mirror = _mirror(runtime.validation_workspace, runtime.branch_id, runtime.attempt_id)
    mirror.owned.update(runtime.required_artifact_paths)
    mirror.inputs = runtime.branch_inputs
    for key in ("_runtime_implementation_contract", "_runtime_frontier_contract"):
        mirror.owned.update((runtime.branch_inputs.get(key) or {}).get("write_set") or [])
    shell = getattr(runtime.tools, "_tools", {}).get("shell")
    result = mirror.run(call.arguments.get("command"), context=context,
                        timeout=getattr(shell, "timeout_seconds", 30),
                        max_output_chars=getattr(shell, "max_output_chars", 20000))
    runtime.tracer.emit("g1_branch_shell_completed", scope_id=runtime.scope_id,
                        tool_call_id=call.id, isolation=result.get("g1_isolation"),
                        committed_owned_paths=result.get("committed_owned_paths", []),
                        not_committed_paths=result.get("not_committed_paths", []),
                        source_conflicts=result.get("source_conflicts", []))
    return result


def _assertion_is_nontrivial(node):
    if isinstance(node, ast.Assert):
        return not isinstance(node.test, ast.Constant)
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr.startswith("assert"):
        if node.func.attr in {"assertRaises", "assertRaisesRegex", "assertWarns", "assertWarnsRegex"}:
            return True
        if not node.args or all(isinstance(arg, ast.Constant) for arg in node.args):
            return False
        if len(node.args) >= 2 and ast.dump(node.args[0]) == ast.dump(node.args[1]):
            return False
        return True
    return False


def _unit_check(root, script, owned):
    """Executed inside Landlock; profile proves candidate code was really called."""
    root = Path(root).resolve()
    script = _safe(root, script)
    module_ast = ast.parse(script.read_text(encoding="utf-8"))
    tests = [node for node in ast.walk(module_ast) if isinstance(node, ast.FunctionDef) and node.name.startswith("test")]
    meaningful = [node for node in tests if any(_assertion_is_nontrivial(n) for n in ast.walk(node))]
    if not meaningful:
        print(MARKER + json.dumps(dict(status="TEST_SETUP_ERROR", error="No non-placeholder unittest assertion", actual_cases=0, candidate_calls=0)))
        return 1
    sys.path.insert(0, str(root))
    spec = importlib.util.spec_from_file_location("_g1_branch_unittest", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    suite = unittest.defaultTestLoader.loadTestsFromModule(module)
    calls = []
    owned = {str(_safe(root, name).resolve()) for name in owned if name.endswith(".py")}
    def profile(frame, event, arg):
        if event == "call" and str(Path(frame.f_code.co_filename).resolve()) in owned:
            if frame.f_code.co_name != "<module>":
                names = frame.f_code.co_varnames[:frame.f_code.co_argcount]
                values = {name: frame.f_locals.get(name) for name in names}
                encoded = json.dumps(values, sort_keys=True, ensure_ascii=False, default=str)
                calls.append({"path":str(Path(frame.f_code.co_filename).relative_to(root)),
                              "function":frame.f_code.co_name,
                              "input_sha256":hashlib.sha256(encoded.encode()).hexdigest(),
                              "argument_types":{name:type(value).__name__ for name,value in values.items()}})
    sys.setprofile(profile)
    try:
        result = unittest.TextTestRunner(stream=sys.stdout, verbosity=2).run(suite)
    finally:
        sys.setprofile(None)
    passed = result.wasSuccessful() and result.testsRun > 0 and bool(calls)
    status = "PASS_LOCAL_FIXTURE" if passed else "CANDIDATE_MISMATCH" if not result.wasSuccessful() else "TEST_SETUP_ERROR"
    print(MARKER + json.dumps(dict(status=status, actual_cases=result.testsRun,
          passed_cases=result.testsRun-len(result.failures)-len(result.errors), candidate_calls=len(calls),
          called_interfaces=calls[:80], errors=len(result.errors), failures=len(result.failures),
          error=None if passed else "Candidate assertions failed or no owned implementation was called")))
    return 0 if passed else 1


def _real_entry_check(checks, entry, contract, output, expected):
    """Use true current inputs and no preexisting output, never private fixtures."""
    mirror = BranchMirror(checks.root, checks.branch_id, checks.attempt_id)
    try:
        mirror.sync()
        target = _safe(mirror.path, output)
        if target.exists():
            target.unlink()
        command = shlex.join(["python3", "-B", entry, str(mirror.path), contract])
        check = mirror.run(command, export=False, refresh=False)
        actual = _digest(target)
        passed = check.get("ok") is True and actual == expected
        return dict(target="entry:" + entry, entrypoint=entry, output_path=output,
                    passed=passed, returncode=check.get("returncode"),
                    expected_output_sha256=expected, actual_output_sha256=actual,
                    output=check.get("output", "")[-2400:], error=check.get("error") if actual == expected else (
                        "Entry did not regenerate the delivered output from true current inputs"),
                    isolation="landlock_private_workspace", real_input_validation="passed" if passed else "failed")
    finally:
        shutil.rmtree(mirror.path)


def complete_g1(checks, result, *, call_id, paths, targets, inputs, execute, emit):
    if not enabled():
        return None
    result = copy.deepcopy(result)
    if result.get("ok") is not True:
        return result
    missing = sorted(set(paths) - set(result.get("files", {})))
    if missing:
        return dict(result, ok=False, completion_accepted=False, error="branch_delivery_incomplete", missing_artifact_paths=missing)
    mirror = _mirror(checks.root, checks.branch_id, checks.attempt_id)
    mirror.owned.update(paths)
    mirror.inputs = inputs
    with mirror.lock:
        mirror.sync()
        script = mirror.path / TEST_PATH
        if not script.is_file():
            return dict(result, ok=False, completion_accepted=False, status="TEST_SETUP_ERROR",
                        error="G1 branch local check is missing", required_local_check=TEST_PATH,
                        next_action="Use shell to write ordinary unittest to " + TEST_PATH + "; call the actual owned implementation, assert a visible-contract business result, then deliver again. Do not import a self-check SDK or write fixtures in shared outputs.")
        tracked = checks.tracked_paths(paths, targets, inputs)
        from .branch_test_delivery import source_versions, component_entries
        all_versions = source_versions(checks.root, tracked)
        fixture_tracked = freshness_paths(checks, paths, targets, inputs)
        versions = source_versions(checks.root, fixture_tracked)
        test_hash = _digest(script)
        checks.scope = (tuple(paths), tuple(targets), copy.deepcopy(inputs))
        checked_sources = [name for name in paths if name.endswith(".py")]
        if any(_digest(mirror.path/name) != versions.get(name) for name in checked_sources):
            return dict(result, ok=False, completion_accepted=False, status="TEST_SETUP_ERROR",
                        error="Private candidate source differs from delivered source; commit the owned correction before checking")
        command = shlex.join([sys.executable, "-B", "-P", str(Path(__file__).resolve()), "_unit",
                              str(mirror.path), TEST_PATH, json.dumps(sorted(mirror.owned))])
        started = time.time()
        outcome = mirror.run(command, timeout=30, export=False)
        markers = [line[len(MARKER):] for line in outcome.get("output", "").splitlines() if line.startswith(MARKER)]
        receipt = json.loads(markers[-1]) if markers else dict(status="TEST_SETUP_ERROR", error=outcome.get("error") or outcome.get("output", "")[-1800:], actual_cases=0, candidate_calls=0)
        after = source_versions(checks.root, freshness_paths(checks, paths, targets, inputs))
        private_sources_match = all(_digest(mirror.path/name) == versions.get(name) for name in checked_sources)
        passed = (outcome.get("ok") is True and receipt.get("status") == "PASS_LOCAL_FIXTURE"
                  and versions == after and private_sources_match and _digest(script) == test_hash)
        if not private_sources_match or _digest(script) != test_hash:
            receipt.update(status="TEST_SETUP_ERROR", error="The check changed candidate source or its own script; no verification attestation was issued")
        elif versions != after:
            receipt.update(status="SOURCE_VERSION_CONFLICT", error="Candidate source or declared input changed during the check; rerun on the current version")
        proof = dict(receipt, passed=passed, source_sha256=versions, test_sha256=test_hash,
                     source_version_matches=versions == after, branch_id=checks.branch_id,
                     private_source_version_matches=private_sources_match,
                     attempt_id=checks.attempt_id, seconds=time.time()-started,
                     isolation="landlock_private_workspace", real_input_validation="pending",
                     validation_read_set=sorted(mirror._validation_inputs()), reused=False,
                     fixture_input_sha256={name:_digest(mirror.path/name) for name in sorted(mirror._validation_inputs())},
                     output=outcome.get("output", "")[-3000:])
        emit("g1_branch_local_check_completed", tool_call_id=call_id,
             test_source=script.read_bytes().decode("utf-8", errors="replace"), **proof)
        if not passed:
            return dict(result, ok=False, completion_accepted=False, error=receipt.get("status", "TEST_SETUP_ERROR"),
                        runtime_focused_checks=[proof], next_action="Use this real check receipt to distinguish test setup from candidate mismatch; retain valid assertions, repair the cause and deliver again.")
        tested = [TEST_PATH]
        focused = [proof]
        for target in targets:
            check = mirror.run(shlex.join(["python3", "-B", target]), timeout=30, export=False)
            extra = dict(target=target, passed=check.get("ok") is True, returncode=check.get("returncode"), output=check.get("output", "")[-2400:], isolation="landlock_private_workspace")
            focused.append(extra)
            emit("g1_branch_required_check_completed", tool_call_id=call_id, **extra)
            if not extra["passed"]:
                return dict(result, ok=False, completion_accepted=False, error="branch_focused_check_failed", runtime_focused_checks=focused)
            tested.append(target)
        from .g1_discovery import contract_heuristics_enabled
        entries = component_entries(checks.root, paths) if contract_heuristics_enabled() else []
        missing_real_inputs = sorted(name for name in mirror._validation_inputs() if not (checks.root / name).is_file())
        real_status = "pending"
        if entries and not missing_real_inputs:
            for entry, contract, output in entries:
                started = time.time()
                extra = _real_entry_check(checks, entry, contract, output, result["sha256"][output])
                extra.update(branch_id=checks.branch_id, attempt_id=checks.attempt_id,
                             seconds=time.time()-started, reused=False)
                focused.append(extra)
                emit("branch_entry_selfcheck_completed", tool_call_id=call_id, **extra)
                if not extra["passed"]:
                    return dict(result, ok=False, completion_accepted=False, error="branch_entry_selfcheck_failed",
                                runtime_focused_checks=focused,
                                next_action="Repair the owned entry so true current inputs regenerate the declared output; fixture checks do not waive entry validation.")
                tested.append("entry:" + entry)
            real_status = "passed"
        if real_status == "passed":
            versions = all_versions
        final_tracked = freshness_paths(checks, paths, targets, inputs, real_input_validated=real_status == "passed")
        if versions != source_versions(checks.root, final_tracked):
            return dict(result, ok=False, completion_accepted=False, error="g1_source_version_conflict", runtime_focused_checks=focused)
        result.update(tested_targets=tested, tests_passed=True, verification_scope="g1_local_fixture_verified_integration_pending",
                      runtime_focused_checks=focused, runtime_test_source_sha256=versions,
                      runtime_validation_input_sha256={name:_digest(checks.root/name) for name in sorted(mirror._validation_inputs())},
                      completion_accepted=True, real_input_validation=real_status,
                      missing_validation_inputs=missing_real_inputs)
        token = hashlib.sha256(json.dumps([call_id, result.get("sha256"), focused], sort_keys=True).encode()).hexdigest()
        result["runtime_test_receipt_id"] = token
        checks.attested.add(token)
        return result


if __name__ == "__main__":
    if sys.argv[1] == "_landlock":
        _launcher(sys.argv[2], sys.argv[3])
    elif sys.argv[1] == "_unit":
        raise SystemExit(_unit_check(sys.argv[2], sys.argv[3], json.loads(sys.argv[4])))
