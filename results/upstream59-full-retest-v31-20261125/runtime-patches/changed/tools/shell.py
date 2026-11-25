import os
import hashlib
import re
import signal
import subprocess
import time
from pathlib import Path
from typing import Any

from agent_runtime_demo.tools.base import ToolCancelled, ToolExecutionContext
from agent_runtime_demo.selfcheck_deadline import current_deadline



AUDIT_CODE_SUFFIXES = {".py", ".js", ".ts", ".java", ".c", ".h", ".cpp", ".rs", ".go", ".sh", ".rb", ".php"}
AUDIT_SKIP_DIRS = {"__pycache__", ".git", ".semserve"}
AUDIT_MAX_TOTAL_BYTES = 64 * 1024 * 1024


def _workspace_snapshot(cwd: Path):
    snap = {}
    total = 0
    try:
        it = cwd.rglob("*")
    except OSError:
        return None
    for p in it:
        try:
            if not p.is_file():
                continue
        except OSError:
            continue
        rel = p.relative_to(cwd)
        if any(part in AUDIT_SKIP_DIRS for part in rel.parts):
            continue
        try:
            data = p.read_bytes()
        except OSError:
            continue
        total += len(data)
        if total > AUDIT_MAX_TOTAL_BYTES:
            return None
        is_code = p.suffix.lower() in AUDIT_CODE_SUFFIXES
        snap[str(rel).replace("\\", "/")] = (
            is_code,
            hashlib.sha256(data).hexdigest(),
            data if is_code else None,
        )
    return snap


def _restore_audit(cwd: Path, snap):
    if not snap:
        return None
    reverted = []
    modified_noncode = []
    deleted_code = []
    deleted_noncode = []
    created = []
    seen = set()
    try:
        it = cwd.rglob("*")
    except OSError:
        return None
    for p in it:
        try:
            if not p.is_file():
                continue
        except OSError:
            continue
        rel = p.relative_to(cwd)
        if any(part in AUDIT_SKIP_DIRS for part in rel.parts):
            continue
        key = str(rel).replace("\\", "/")
        seen.add(key)
        if key not in snap:
            created.append(key)
            continue
        is_code, old_hash, old_bytes = snap[key]
        try:
            new_bytes = p.read_bytes()
        except OSError:
            continue
        if hashlib.sha256(new_bytes).hexdigest() == old_hash:
            continue
        if is_code and old_bytes is not None:
            try:
                p.write_bytes(old_bytes)
            except OSError:
                pass
            reverted.append(key)
        else:
            modified_noncode.append(key)
    for key, (is_code, _, old_bytes) in snap.items():
        if key in seen:
            continue
        if is_code and old_bytes is not None:
            try:
                target = cwd / key.replace("/", os.sep)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(old_bytes)
            except OSError:
                pass
            deleted_code.append(key)
        else:
            deleted_noncode.append(key)
    return {
        "reverted_code_files": reverted,
        "modified_non_code_files": modified_noncode,
        "restored_deleted_code_files": deleted_code,
        "deleted_non_code_files": deleted_noncode,
        "created_files": created[:30],
        "created_files_total": len(created),
    }


_audit_holder = {}


class ShellTool:
    name = "shell"
    # Arbitrary commands may mutate any workspace resource, so calls are kept
    # on the registry's conservative global serial lane.
    parallel_safe = False
    read_only = False

    def __init__(self, cwd: Path, timeout_seconds: int = 30, max_output_chars: int = 20_000):
        self.cwd = cwd.resolve()
        if not self.cwd.is_dir():
            raise ValueError(f"Workspace does not exist or is not a directory: {self.cwd}")
        self.timeout_seconds = timeout_seconds
        self.max_output_chars = max_output_chars

    def schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": "Execute one shell command inside the configured workspace. Existing CODE files are write-audited: any modification or deletion made by a shell command is automatically reverted. To modify an existing code file use apply_patch instead. Creating new files and writing test outputs is allowed.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {"type": "string", "description": "Shell command to execute"}
                    },
                    "required": ["command"],
                    "additionalProperties": False,
                },
            },
        }

    def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        return self.execute_with_context(arguments, None)

    def execute_with_context(
        self,
        arguments: dict[str, Any],
        context: ToolExecutionContext | None,
    ) -> dict[str, Any]:
        command = arguments.get("command")
        if not isinstance(command, str) or not command.strip():
            return {"ok": False, "error": "command must be a non-empty string"}
        lowered = command.lower()
        if os.getenv("AGENT_RUNTIME_FORBID_BROWSER_INSTALL", "").lower() in {
            "1",
            "true",
            "yes",
        } and re.search(
            r"(?:playwright\s+install|npm\s+(?:install|i|add)[^\n;]*playwright|"
            r"npx\s+playwright\s+install)",
            lowered,
        ):
            return {
                "ok": False,
                "returncode": -3,
                "output": "",
                "status": "external_browser_install_not_allowed",
                "retryable": False,
                "error": (
                    "browser installation is provided by the separate verifier; "
                    "do not install Playwright or Chromium in the agent container"
                ),
                "next_action": (
                    "use the existing backend smoke test and frontend build, then "
                    "finish so Harbor can run its 28 verifier cases"
                ),
            }
        if re.search(r"(?:^|[;&|]\s*)nohup\s+", lowered):
            return {
                "ok": False,
                "returncode": -4,
                "output": "",
                "status": "detached_process_not_allowed",
                "retryable": False,
                "error": (
                    "detached background processes are outside the Runtime tool "
                    "lifecycle and are not allowed"
                ),
                "next_action": "run a bounded foreground check or finish the task",
            }
        # Never allow a model-authored process-name scan to cross the tool's
        # subprocess boundary.  The Runtime command line can legitimately
        # contain task text such as "uvicorn" or "vite"; walking /proc and
        # killing every matching cmdline can therefore kill the Runtime itself.
        # Exact PIDs created and owned by the task may still be terminated.
        broad_process_kill = (
            ("/proc" in lowered and re.search(r"\bkill\b", lowered))
            or re.search(r"\bpkill\s+(?:-[a-z]*f[a-z]*|--full)\b", lowered)
            or re.search(r"\bkillall\b", lowered)
        )
        if broad_process_kill:
            return {
                "ok": False,
                "returncode": -5,
                "output": "",
                "status": "broad_process_kill_not_allowed",
                "retryable": False,
                "state_changed": False,
                "error": (
                    "broad process-name or /proc scanning kills can terminate "
                    "the Runtime and are not allowed"
                ),
                "next_action": (
                    "terminate only an exact task-owned PID recorded when the "
                    "service was started, use a different unused port, or finish "
                    "and let Harbor run the verifier"
                ),
            }
        blocked_patterns = (
            r"\.\.[\\/]",
            r"(?<![a-z0-9_])[a-z]:[\\/]",
            r"(?:turns|trace|api_events|wire_requests|execution_state)\.jsonl",
            r"get-childitem\s+env",
            r"\$env:",
            r"os\.environ",
        )
        if any(re.search(pattern, lowered) for pattern in blocked_patterns):
            return {
                "ok": False,
                "returncode": -2,
                "output": "",
                "error": "shell command rejected: access is restricted to the task workspace",
            }

        phase_deadline = current_deadline()
        if phase_deadline is not None and time.monotonic() >= phase_deadline:
            return {'ok':False,'returncode':124,'output':'','status':'selfcheck_budget_exhausted',
                    'state_changed':False,'error':'Self-check deadline expired before shell launch'}
        _audit_holder['audit'] = None
        _snap = _workspace_snapshot(self.cwd)
        process = subprocess.Popen(
            command,
            cwd=self.cwd,
            shell=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            start_new_session=os.name == "posix",
        )
        deadline = time.monotonic() + self.timeout_seconds
        phase_limited = phase_deadline is not None and phase_deadline <= deadline
        if phase_limited:
            deadline = phase_deadline
        while True:
            try:
                output, _ = process.communicate(timeout=0.05)
                break
            except subprocess.TimeoutExpired:
                if context is not None and context.cancelled:
                    output = self._terminate_process(process)
                    raise ToolCancelled(
                        f"shell command cancelled: node={context.node_id}"
                    )
                if time.monotonic() >= deadline:
                    # A shell may exit while a descendant still holds stdout.
                    # Kill this owned process group at the phase deadline too.
                    if phase_limited and os.name == 'posix':
                        try:os.killpg(process.pid, signal.SIGKILL)
                        except ProcessLookupError:pass
                    output = self._terminate_process(process, graceful=False)
                    return self._output_receipt({
                        "ok": False,
                        "returncode": -1,
                        "status": "selfcheck_budget_exhausted" if phase_limited else "tool_timeout_no_progress",
                        "retryable": False,
                        "state_changed": False,
                        "same_operation_retry_forbidden": True,
                        "error": "Self-check absolute deadline expired" if phase_limited else f"Command timed out after {self.timeout_seconds} seconds",
                        "next_action": (
                            "do not retry the same operation with a longer inner timeout, "
                            "nohup, sleep polling, or a different shell wrapper"
                        ),
                    }, output.replace("\x00", ""))

        output = output.replace("\x00", "")
        if phase_deadline is not None and time.monotonic() >= phase_deadline:
            return self._output_receipt({'ok':False,'returncode':process.returncode,
                    'status':'selfcheck_budget_exhausted','completed':False,
                    'error':'Shell completed after the self-check deadline; self-check remains incomplete'}, output)
        _audit = _restore_audit(self.cwd, _snap) if _snap else None
        if _audit and (_audit['reverted_code_files'] or _audit['restored_deleted_code_files']):
            reverted = _audit['reverted_code_files'] + _audit['restored_deleted_code_files']
            output += (
                '\n[workspace-write-audit] shell modified or deleted existing code file(s): '
                + ', '.join(reverted[:10])
                + (', ...' if len(reverted) > 10 else '')
                + '. These changes were REVERTED. To modify existing code files use apply_patch.\n'
            )
        _audit_holder['audit'] = _audit
        result = {
            "ok": process.returncode == 0,
            "returncode": process.returncode,
        }
        if process.returncode != 0:
            result.update(status='process_error', error_type='ProcessExitError',
                          error=f'Command exited with code {process.returncode}.\n'+output[-1800:],
                          next_action='Use the output and exit code to locate the failed command, test, or import. Correct the cause and rerun; command completion is not test success.')
        return self._output_receipt(result, output)

    def _output_receipt(self, result: dict[str, Any], output: str) -> dict[str, Any]:
        if _audit_holder.get('audit') is not None:
            result['workspace_write_audit'] = _audit_holder['audit']
        result['output'] = output[-self.max_output_chars:]
        if len(output) > self.max_output_chars:
            result.update(truncated=True, full_output_chars=len(output))
            # Use the existing Runtime-owned review directory, excluded from
            # candidate/spec snapshots. Logs must not become business progress.
            relative=Path('.semserve/visible_checks/tool-output')/(hashlib.sha256(output.encode('utf8')).hexdigest()+'.log')
            target=self.cwd/relative
            try:
                if not target.resolve().is_relative_to(self.cwd):
                    raise ValueError('Runtime output path escapes workspace')
                target.parent.mkdir(parents=True,exist_ok=True)
                target.write_text(output,encoding='utf8')
                result['output_path']=relative.as_posix()
                result['output_sha256']=hashlib.sha256(target.read_bytes()).hexdigest()
            except (OSError,ValueError) as exc:
                result['output_storage_error']=str(exc)
        return result

    @staticmethod
    def _terminate_process(
        process: subprocess.Popen[str],
        *,
        graceful: bool = True,
    ) -> str:
        if process.poll() is None:
            if os.name == "posix":
                os.killpg(process.pid, signal.SIGTERM if graceful else signal.SIGKILL)
            elif graceful:
                process.terminate()
            else:
                process.kill()
        if graceful:
            try:
                output, _ = process.communicate(timeout=1.0)
                return output
            except subprocess.TimeoutExpired:
                if os.name == "posix":
                    os.killpg(process.pid, signal.SIGKILL)
                else:
                    process.kill()
        output, _ = process.communicate()
        return output
