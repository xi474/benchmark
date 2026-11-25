from __future__ import annotations

import hashlib
import json
from pathlib import Path
import threading
from typing import Any, Iterable
from agent_runtime_demo.dynamic_frontier import MAX_FRONTIER_CANDIDATES, g1_enabled

from agent_runtime_demo.frontier_contract import (
    FRONTIER_REPORT_MAX_BYTES,
    FRONTIER_REPORT_LIMITS,
    compact_frontier_report_payload,
    is_frontier_report_path,
    validate_frontier_report,
)


IGNORED_DIRECTORIES = frozenset({".git", ".venv", "__pycache__", "node_modules"})
MAX_DIRECT_WRITE_CHARS = 8_192
# A parsed tool call is already complete JSON, so a larger ordered chunk does
# not carry the truncation risk of a half-emitted write_file call. Keep a
# bounded limit while avoiding retry loops for normal 10-30 KiB source files.
MAX_CHUNK_WRITE_CHARS = 32_768


class WorkspaceAccess:
    """Path-confined filesystem operations shared by native and MCP tools."""

    def __init__(self, root: Path, max_file_chars: int = 1_000_000):
        self.authored_paths: set[str] = set()  # absolute paths the agent created/modified
        self.root = root.resolve()
        if not self.root.is_dir():
            raise ValueError(f"Workspace does not exist or is not a directory: {self.root}")
        self.max_file_chars = max_file_chars
        self._write_lock = threading.RLock()

    def resolve(self, path: str, *, must_exist: bool = True) -> Path:
        if not isinstance(path, str) or not path.strip():
            raise ValueError("path must be a non-empty string")
        candidate = Path(path)
        if not candidate.is_absolute():
            candidate = self.root / candidate
        resolved = candidate.resolve(strict=False)
        if not resolved.is_relative_to(self.root):
            raise ValueError(f"Path escapes workspace: {path}")
        if must_exist:
            resolved = candidate.resolve(strict=True)
        return resolved

    def relative(self, path: Path) -> str:
        value = path.relative_to(self.root).as_posix()
        return value or "."

    def read_text(self, path: str, max_chars: int = 100_000) -> dict[str, Any]:
        target = self.resolve(path)
        if not target.is_file():
            raise ValueError(f"Not a file: {path}")
        limit = self._bounded_limit(max_chars, 1, self.max_file_chars, "max_chars")
        text = target.read_text(encoding="utf-8")
        return {
            "ok": True,
            "path": self.relative(target),
            "content": text[:limit],
            "chars": len(text),
            "truncated": len(text) > limit,
        }

    def list_files(
        self,
        path: str = ".",
        recursive: bool = False,
        max_entries: int = 500,
    ) -> dict[str, Any]:
        target = self.resolve(path)
        limit = self._bounded_limit(max_entries, 1, 5_000, "max_entries")
        if target.is_file():
            candidates: Iterable[Path] = [target]
        elif recursive:
            candidates = target.rglob("*")
        else:
            candidates = target.iterdir()

        entries: list[dict[str, Any]] = []
        truncated = False
        for candidate in candidates:
            if any(part in IGNORED_DIRECTORIES for part in candidate.relative_to(self.root).parts):
                continue
            try:
                resolved = candidate.resolve()
            except OSError:
                continue
            if not resolved.is_relative_to(self.root):
                continue
            if len(entries) >= limit:
                truncated = True
                break
            entries.append(
                {
                    "path": self.relative(candidate),
                    "type": "directory" if candidate.is_dir() else "file",
                }
            )
        entries.sort(key=lambda item: item["path"])
        return {"ok": True, "entries": entries, "truncated": truncated}

    def search_text(
        self,
        query: str,
        path: str = ".",
        case_sensitive: bool = False,
        max_matches: int = 100,
    ) -> dict[str, Any]:
        if not isinstance(query, str) or not query:
            raise ValueError("query must be a non-empty string")
        target = self.resolve(path)
        limit = self._bounded_limit(max_matches, 1, 1_000, "max_matches")
        files = [target] if target.is_file() else target.rglob("*")
        needle = query if case_sensitive else query.casefold()
        matches: list[dict[str, Any]] = []
        truncated = False
        for candidate in files:
            if not candidate.is_file():
                continue
            relative_parts = candidate.relative_to(self.root).parts
            if any(part in IGNORED_DIRECTORIES for part in relative_parts):
                continue
            try:
                if not candidate.resolve().is_relative_to(self.root):
                    continue
                text = candidate.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            for number, line in enumerate(text.splitlines(), start=1):
                haystack = line if case_sensitive else line.casefold()
                if needle not in haystack:
                    continue
                if len(matches) >= limit:
                    truncated = True
                    break
                matches.append(
                    {
                        "path": self.relative(candidate),
                        "line": number,
                        "text": line[:500],
                    }
                )
            if truncated:
                break
        return {"ok": True, "matches": matches, "truncated": truncated}

    def write_text(
        self,
        path: str,
        content: str,
        overwrite: bool = False,
        *,
        max_chars: int = MAX_DIRECT_WRITE_CHARS,
    ) -> dict[str, Any]:
        if not isinstance(content, str):
            raise ValueError("content must be a string")
        if len(content) > max_chars:
            raise ValueError(
                f"content exceeds the direct-write limit of {max_chars} characters; "
                "use write_file_chunk with ordered expected_offset values"
            )
        target = self.resolve(path, must_exist=False)
        parent = target.parent.resolve(strict=False)
        if not parent.is_relative_to(self.root):
            raise ValueError(f"Parent path escapes workspace: {path}")
        parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and not overwrite:
            raise FileExistsError(f"File already exists; set overwrite=true: {path}")
        # Replayed join artifacts must not touch mtime or retrigger builds. Check
        # live bytes, not a call cache: A -> B -> A must still restore A.
        unchanged = False
        if overwrite and target.is_file():
            try:
                unchanged = target.read_bytes() == content.encode("utf-8")
            except OSError:
                pass  # An optimization must not require read permission to write.
        if unchanged:
            return {"ok": True, "path": self.relative(target), "chars_written": 0,
                    "overwritten": True,
                    "unchanged": True, "write_performed": False}
        target.write_text(content, encoding="utf-8")
        return {
            "ok": True,
            "path": self.relative(target),
            "chars_written": len(content),
            "overwritten": overwrite,
        }

    def write_chunk(
        self,
        path: str,
        content: str,
        expected_offset: int,
        *,
        truncate: bool = False,
    ) -> dict[str, Any]:
        if not isinstance(content, str):
            raise ValueError("content must be a string")
        if len(content) > MAX_CHUNK_WRITE_CHARS:
            raise ValueError(
                f"chunk exceeds {MAX_CHUNK_WRITE_CHARS} characters"
            )
        if not isinstance(expected_offset, int) or isinstance(expected_offset, bool):
            raise ValueError("expected_offset must be an integer")
        if expected_offset < 0:
            raise ValueError("expected_offset must be non-negative")
        if truncate and expected_offset != 0:
            raise ValueError("truncate=true requires expected_offset=0")
        target = self.resolve(path, must_exist=False)
        parent = target.parent.resolve(strict=False)
        if not parent.is_relative_to(self.root):
            raise ValueError(f"Parent path escapes workspace: {path}")
        parent.mkdir(parents=True, exist_ok=True)
        with self._write_lock:
            existing = ""
            if target.exists() and not truncate:
                if not target.is_file():
                    raise ValueError(f"Not a file: {path}")
                existing = target.read_text(encoding="utf-8")
            if len(existing) != expected_offset:
                raise ValueError(
                    f"chunk offset mismatch for {path}: expected {expected_offset}, "
                    f"actual {len(existing)}"
                )
            updated = content if truncate else existing + content
            if len(updated) > self.max_file_chars:
                raise ValueError(f"file exceeds {self.max_file_chars} characters")
            target.write_text(updated, encoding="utf-8")
            raw = updated.encode("utf-8")
        return {
            "ok": True,
            "path": self.relative(target),
            "chars_written": len(content),
            "next_offset": len(updated),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "truncated_before_write": truncate,
        }

    def snapshot_token(self, path: str, *, recursive: bool = False) -> str:
        """Hash metadata relevant to a read-only workspace operation."""

        target = self.resolve(path)
        candidates = [target]
        if target.is_dir():
            candidates = list(target.rglob("*")) if recursive else list(target.iterdir())
        digest = hashlib.sha256()
        for candidate in sorted(candidates, key=lambda item: item.as_posix()):
            try:
                resolved = candidate.resolve()
                if not resolved.is_relative_to(self.root):
                    continue
                relative = resolved.relative_to(self.root).as_posix()
                if any(part in IGNORED_DIRECTORIES for part in Path(relative).parts):
                    continue
                stat = resolved.stat()
            except OSError:
                continue
            digest.update(relative.encode("utf-8", errors="surrogatepass"))
            digest.update(str(stat.st_mtime_ns).encode("ascii"))
            digest.update(str(stat.st_size).encode("ascii"))
        return digest.hexdigest()

    @staticmethod
    def _bounded_limit(value: int, minimum: int, maximum: int, name: str) -> int:
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError(f"{name} must be an integer")
        if not minimum <= value <= maximum:
            raise ValueError(f"{name} must be between {minimum} and {maximum}")
        return value


class ReadFileTool:
    name = "read_file"
    parallel_safe = True
    read_only = True
    speculation_safe = True

    def __init__(self, workspace: WorkspaceAccess):
        self.workspace = workspace

    def schema(self) -> dict[str, Any]:
        return _schema(
            self.name,
            "Read a UTF-8 text file inside the configured workspace.",
            {
                "path": {"type": "string"},
                "max_chars": {"type": "integer", "minimum": 1, "maximum": 1_000_000},
            },
            ["path"],
        )

    def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        return self.workspace.read_text(
            arguments.get("path", ""), arguments.get("max_chars", 100_000)
        )

    def speculation_snapshot(self, arguments: dict[str, Any]) -> str:
        return self.workspace.snapshot_token(arguments.get("path", ""))


class ListFilesTool:
    name = "list_files"
    parallel_safe = True
    read_only = True
    speculation_safe = True

    def __init__(self, workspace: WorkspaceAccess):
        self.workspace = workspace

    def schema(self) -> dict[str, Any]:
        return _schema(
            self.name,
            "List files and directories inside the configured workspace.",
            {
                "path": {"type": "string", "default": "."},
                "recursive": {"type": "boolean", "default": False},
                "max_entries": {"type": "integer", "minimum": 1, "maximum": 5_000},
            },
            [],
        )

    def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        return self.workspace.list_files(
            arguments.get("path", "."),
            arguments.get("recursive", False),
            arguments.get("max_entries", 500),
        )

    def speculation_snapshot(self, arguments: dict[str, Any]) -> str:
        return self.workspace.snapshot_token(
            arguments.get("path", "."), recursive=arguments.get("recursive", False)
        )


class SearchTextTool:
    name = "search_text"
    parallel_safe = True
    read_only = True
    speculation_safe = True

    def __init__(self, workspace: WorkspaceAccess):
        self.workspace = workspace

    def schema(self) -> dict[str, Any]:
        return _schema(
            self.name,
            "Search for literal text in UTF-8 files inside the workspace.",
            {
                "query": {"type": "string"},
                "path": {"type": "string", "default": "."},
                "case_sensitive": {"type": "boolean", "default": False},
                "max_matches": {"type": "integer", "minimum": 1, "maximum": 1_000},
            },
            ["query"],
        )

    def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        return self.workspace.search_text(
            arguments.get("query", ""),
            arguments.get("path", "."),
            arguments.get("case_sensitive", False),
            arguments.get("max_matches", 100),
        )

    def speculation_snapshot(self, arguments: dict[str, Any]) -> str:
        return self.workspace.snapshot_token(arguments.get("path", "."), recursive=True)


def _looks_like_placeholder(content: str) -> bool:
    """Heuristic: tiny stub files (<=2 non-empty lines) that are clearly placeholders."""
    if content is None:
        return False
    lines = [ln for ln in content.strip().splitlines() if ln.strip()]
    if not lines:
        return True
    if len(lines) > 2:
        return False
    joined = " ".join(ln.strip().lstrip("#").strip().lower() for ln in lines)
    if any(k in joined for k in ("todo", "placeholder", "stub", "notimplemented", "not implemented")):
        return True
    if all(ln.strip().startswith(("#", "//", "--", "<!--")) for ln in lines):
        return True
    return False


class WriteFileTool:
    name = "write_file"
    parallel_safe = False
    read_only = False

    def __init__(self, workspace: WorkspaceAccess):
        self.workspace = workspace

    def schema(self) -> dict[str, Any]:
        return _schema(
            self.name,
            "Create a NEW UTF-8 text file of at most 8192 characters. "
            "You may overwrite a file only if you created it yourself this session "
            "or if it is an explicit placeholder stub; otherwise every modification "
            "of an existing file MUST use apply_patch. "
            "For larger new files use ordered write_file_chunk calls.",
            {
                "path": {"type": "string"},
                "content": {"type": "string", "maxLength": MAX_DIRECT_WRITE_CHARS},
                "overwrite": {"type": "boolean", "default": False},
            },
            ["path", "content", "overwrite"],
        )

    def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        import difflib
        import hashlib
        
        if "overwrite" not in arguments or not isinstance(arguments.get("overwrite"), bool):
            return {
                "ok": False,
                "error": (
                    "write_file requires an explicit boolean overwrite choice; "
                    "use overwrite=true only after inspecting an existing target"
                ),
            }
        path = arguments.get("path", "")
        content = arguments.get("content")
        if is_frontier_report_path(path):
            raise ValueError(
                "Runtime frontier reports must be materialized and completed atomically with "
                "deliver_frontier_report; do not use write_file"
            )
        
        # SAFETY: before overwriting existing files, verify agent has read them
        # and detect if file was modified since last read (concurrent changes)
        overwrite = arguments["overwrite"]
        file_path = self.workspace.resolve(path, must_exist=False)
        
        authored = self.workspace.authored_paths
        resolved_key = str(file_path)
        if file_path.exists() and overwrite:
            # CONDITIONAL GATE (default config): overwrite allowed for files the agent
            # authored this session and for explicit placeholder stubs; everything else
            # must go through apply_patch.
            allowed = resolved_key in authored
            if not allowed:
                try:
                    existing = file_path.read_text(encoding="utf-8")
                except Exception:
                    existing = ""
                if _looks_like_placeholder(existing):
                    allowed = True
            if not allowed:
                return {
                    "ok": False,
                    "status": "tool_error",
                    "error": "write_file cannot overwrite this existing file. It was not "
                             "created by you this session and is not a placeholder stub. "
                             "Use apply_patch (path, old_text, new_text) for modifications "
                             "of existing non-placeholder files. write_file is for creating "
                             "new files, rewriting your own files, or filling placeholder stubs.",
                    "hint": "Call apply_patch with the exact current content as old_text and "
                            "the replacement as new_text. Re-read the file first if you do not "
                            "have the exact current content.",
                }
        result = self.workspace.write_text(path, content, overwrite)
        if result.get("ok"):
            authored.add(resolved_key)
        return result


class WriteFileChunkTool:
    name = "write_file_chunk"
    parallel_safe = False
    read_only = False

    def __init__(self, workspace: WorkspaceAccess):
        self.workspace = workspace

    def schema(self) -> dict[str, Any]:
        return _schema(
            self.name,
            "Write one ordered UTF-8 file chunk (maximum 32768 characters). "
            "Use truncate=true and expected_offset=0 for the first chunk, then pass "
            "the returned next_offset for each later chunk. Offset checks prevent lost updates.",
            {
                "path": {"type": "string"},
                "content": {"type": "string", "maxLength": MAX_CHUNK_WRITE_CHARS},
                "expected_offset": {"type": "integer", "minimum": 0},
                "truncate": {"type": "boolean", "default": False},
            },
            ["path", "content", "expected_offset", "truncate"],
        )

    def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        path = arguments.get("path", "")
        content = arguments.get("content")
        expected_offset = arguments.get("expected_offset")
        if is_frontier_report_path(path):
            raise ValueError(
                "Runtime frontier reports must be materialized and completed atomically with "
                "deliver_frontier_report; do not use write_file_chunk"
            )
        return self.workspace.write_chunk(
            path,
            content,
            expected_offset,
            truncate=arguments.get("truncate", False),
        )


class DeliverFrontierReportTool:
    """Atomically validate, materialize and deliver one bounded frontier report."""

    name = "deliver_frontier_report"
    parallel_safe = False
    read_only = False

    def __init__(self, workspace: WorkspaceAccess):
        self.workspace = workspace

    def schema(self) -> dict[str, Any]:
        properties: dict[str, Any] = {
            "path": {"type": "string", "minLength": 1},
            "surface": {"type": "string", "minLength": 1, "maxLength": 32},
        }
        for field, (max_items, max_chars) in FRONTIER_REPORT_LIMITS.items():
            properties[field] = {
                "type": "array",
                "maxItems": max_items,
                "items": {"type": "string", "minLength": 1, "maxLength": max_chars},
            }
        return _schema(
            self.name,
            "Finish one Runtime-derived investigation branch. Submit only compact, "
            "decision-critical facts in the fixed schema. Runtime validates the byte and field "
            "budgets, writes the JSON report, attests it, and ends the branch atomically. "
            "Do not include raw source dumps or exhaustive field/control lists.",
            properties,
            ["path", "surface", *FRONTIER_REPORT_LIMITS],
        )

    def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        required = {"path", "surface", *FRONTIER_REPORT_LIMITS}
        if set(arguments) != required:
            raise ValueError(
                "deliver_frontier_report requires exactly path, surface, source_files, "
                "critical_invariants, interfaces, and open_questions"
            )
        path = arguments["path"]
        if not is_frontier_report_path(path):
            raise ValueError(
                "deliver_frontier_report path must be .semserve/frontier/*-evidence.json"
            )
        expected_surface = path[
            len(".semserve/frontier/"):-len("-evidence.json")
        ]
        payload = {
            "surface": arguments["surface"],
            **{field: arguments[field] for field in FRONTIER_REPORT_LIMITS},
        }
        payload, compaction = compact_frontier_report_payload(payload)
        content = json.dumps(
            payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ) + "\n"
        raw = content.encode("utf-8")
        validate_frontier_report(raw, expected_surface=expected_surface)
        # This path is allowed to exceed the ordinary one-shot write limit only
        # after fixed-schema validation and Runtime compaction. Keeping the
        # exception inside this atomic tool prevents arbitrary large writes and
        # avoids an impossible write_file_chunk handoff for frontier reports.
        write_result = self.workspace.write_text(
            path,
            content,
            overwrite=True,
            max_chars=FRONTIER_REPORT_MAX_BYTES,
        )
        digest = hashlib.sha256(raw).hexdigest()
        return {
            "ok": True,
            "files": {path: content},
            "sha256": {path: digest},
            "bytes_written": len(raw),
            "runtime_compaction": compaction,
            "write_result": write_result,
            "verification_scope": "runtime_frontier_schema_and_file_integrity",
            "tested_targets": [],
            "tests_passed": None,
        }

    def extract_verified_artifact(self, arguments, result):
        return {
            "kind": "file",
            "content": json.dumps(result["files"], ensure_ascii=False),
            "file_sha256": result["sha256"],
            "tested_targets": [],
            "tests_passed": None,
            "verification_scope": "runtime_frontier_schema_and_file_integrity",
            "runtime_compaction": result.get("runtime_compaction"),
            "completes_branch": True,
        }


class ReportFrontierStateTool:
    """Carry an executor-authored frontier delta through a real tool result.

    Some OpenAI-compatible backends omit assistant ``content`` whenever a turn
    contains function calls.  A dedicated tool keeps the same advisory state
    contract available at that boundary while letting Runtime validate and
    accumulate it only after successful execution.
    """

    name = "report_frontier_state"
    parallel_safe = False
    read_only = False

    def schema(self) -> dict[str, Any]:
        work_unit = {
            "type": "object",
            "properties": {
                "work_unit_id": {"type": "string", "maxLength": 80},
                "kind": {"type": "string", "maxLength": 48},
                "surface": {"type": "string", "maxLength": 48},
                "goal": {"type": "string", "minLength": 1, "maxLength": 160},
                "needs": {
                    "type": "array", "maxItems": 6,
                    "items": {"type": "string", "maxLength": 160},
                },
                "read_set": {
                    "type": "array", "maxItems": 12,
                    "items": {"type": "string", "maxLength": 2048},
                },
                "write_set": {
                    "type": "array", "maxItems": 12,
                    "items": {"type": "string", "maxLength": 2048},
                },
                "evidence_ids": {
                    "type": "array", "maxItems": 12,
                    "items": {"type": "string", "maxLength": 160},
                },
                "focused_check": {"type": "string", "maxLength": 640},
                "completion_contract": {
                    "type": "object",
                    "properties": {
                        "required_artifact_paths": {
                            "type": "array", "maxItems": 12,
                            "items": {"type": "string", "maxLength": 2048},
                        },
                        "required_test_targets": {
                            "type": "array", "maxItems": 4,
                            "items": {"type": "string", "maxLength": 320},
                        },
                    },
                    "required": ["required_artifact_paths", "required_test_targets"],
                    "additionalProperties": False,
                },
                "workload_hint": {
                    "type": "string", "enum": ["easy", "medium", "hard"],
                },
            },
            "required": [
                "work_unit_id", "kind", "surface", "goal", "needs",
                "read_set", "write_set", "focused_check",
                "completion_contract", "workload_hint",
            ],
            "additionalProperties": False,
        }
        from agent_runtime_demo.qwen_frontier_predictor import BRANCH_PROFILE_LEVELS, branch_profiles_enabled

        profile_description = ""
        if branch_profiles_enabled():
            work_unit["properties"].update({
                "difficulty": {
                    "type": "string", "enum": list(BRANCH_PROFILE_LEVELS["difficulty"]),
                    "description": "Estimate remaining implementation and verification difficulty: low, medium, or high.",
                },
                "length": {
                    "type": "string", "enum": list(BRANCH_PROFILE_LEVELS["length"]),
                    "description": "Estimate the remaining work relative to the other branches: short, medium, or long.",
                },
            })
            work_unit["required"].extend(BRANCH_PROFILE_LEVELS)
            profile_description = (
                " For every ready_upsert item, provide both difficulty (low, medium, high) "
                "and length (short, medium, long) for its remaining work. "
                "Estimate complexity separately from duration using the visible implementation "
                "and focused check. workload_hint alone is insufficient."
            )
        if g1_enabled():
            work_unit["properties"].update({
                "validation_read_set": {
                    "type": "array", "maxItems": 12,
                    "items": {"type": "string", "maxLength": 2048},
                    "description": "Real upstream artifacts required for validation, separate from current coding reads.",
                },
                "validation_mode": {
                    "type": "string", "enum": ["isolated_fixture", "materialized_inputs"],
                    "description": "Private-fixture checks may precede real upstream artifacts; materialized checks must wait for them.",
                },
            })
        short_list = {
            "type": "array", "maxItems": MAX_FRONTIER_CANDIDATES,
            "items": {"type": "string", "maxLength": 160},
        }
        return _schema(
            self.name,
            "Report only the changed execution state and currently executable semantic work "
            "units. Runtime validates observed reads, workspace-local disjoint writes, and "
            "completion contracts before any unit reaches the predictor. This is advisory "
            "state, not a DAG, action, width, or offer decision. Use it only in the dedicated "
            "report-only turn requested by Runtime. Report independent work before the parent "
            "writes its outputs, never after; it may cite only earlier completed tool results."
            + profile_description,
            {
                "phase": {
                    "type": "string",
                    "enum": ["inspect", "implement", "validate", "integrate", "blocked", "done"],
                },
                "done_add": short_list,
                "ready_upsert": {
                    "type": "array", "maxItems": MAX_FRONTIER_CANDIDATES, "items": work_unit,
                },
                "ready_remove": short_list,
                "blocked_add": short_list,
                "active_add": short_list,
                "active_remove": short_list,
            },
            [
                "phase", "done_add", "ready_upsert", "ready_remove",
                "blocked_add", "active_add", "active_remove",
            ],
        )

    def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        # Reuse the same bounded normalizer as the legacy assistant-text
        # transport. Import lazily to keep the workspace tool module lightweight.
        from agent_runtime_demo.qwen_frontier_predictor import (
            BRANCH_PROFILE_LEVELS, branch_profiles_enabled, normalize_execution_delta,
        )

        delta = normalize_execution_delta(arguments)
        if delta is None:
            raise ValueError("invalid frontier state delta")
        if branch_profiles_enabled():
            invalid_candidates = [
                {"index": index, "work_unit_id": candidate["work_unit_id"]}
                for index, candidate in enumerate(delta["ready_upsert"])
                if any(field not in candidate for field in BRANCH_PROFILE_LEVELS)
            ]
            if invalid_candidates:
                return {
                    "ok": False,
                    "accepted": False,
                    "status": "invalid_frontier_branch_profile",
                    "invalid_candidates": invalid_candidates,
                    "error": "Every ready_upsert candidate requires valid difficulty and length values.",
                    "next_action": (
                        "Keep the supported candidates and resubmit their estimates. Use "
                        "difficulty=low|medium|high and length=short|medium|long for each candidate."
                    ),
                }
        return {
            "ok": True,
            "accepted": True,
            "delta": delta,
            "authority": "advisory_pending_runtime_evidence_validation",
        }


class DeliverFilesTool:
    """Attest existing UTF-8 files; never infer correctness or test success."""
    name = "deliver_files"
    parallel_safe = False
    read_only = True

    def __init__(self, workspace: WorkspaceAccess):
        self.workspace = workspace

    def schema(self) -> dict[str, Any]:
        return _schema(self.name,
            "Deliver your completed branch's assigned UTF-8 output files. Reads actual files "
            "and attests their contents and SHA256. Once all assigned paths match the branch "
            "contract, Runtime ends the branch and joins its delivery. This file tool itself "
            "does not certify tests. For declared required_test_targets, Runtime additionally "
            "executes or reuses version-matched checks before accepting completion. Use returned "
            "missing paths or check failures to repair; unchanged resubmission is not progress. "
            "Missing files are errors.",
            {"paths": {"type": "array", "items": {"type": "string", "minLength": 1},
                       "minItems": 1, "maxItems": 32, "uniqueItems": True}}, ["paths"])

    def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        paths = arguments.get("paths")
        if set(arguments) != {"paths"} or not isinstance(paths, list) or not 1 <= len(paths) <= 32:
            raise ValueError("Provide only a nonempty paths array (at most 32 files)")
        contents, hashes = {}, {}
        total = 0
        for path in paths:
            if (not isinstance(path, str) or not path or path.startswith("/")
                    or "\\" in path or ":" in path or any(p in {"", ".", ".."} for p in path.split("/"))):
                raise ValueError("Delivery paths must be normalized workspace-relative paths")
            if path in contents:
                raise ValueError("Duplicate delivery path")
            target = self.workspace.resolve(path)
            if not target.is_file() or not target.is_relative_to(self.workspace.root):
                raise ValueError("Delivery requires an existing workspace file")
            # Bound materialized payloads before reading, then check actual byte count.
            if target.stat().st_size > 1_000_000:
                raise ValueError("Delivery file exceeds 1 MB")
            raw = target.read_bytes()
            if is_frontier_report_path(path):
                expected_surface = path[
                    len(".semserve/frontier/"):-len("-evidence.json")
                ]
                validate_frontier_report(raw, expected_surface=expected_surface)
            total += len(raw)
            if total > 2_000_000:
                raise ValueError("Delivery exceeds 2 MB")
            contents[path] = raw.decode("utf-8")
            hashes[path] = hashlib.sha256(raw).hexdigest()
        return {"ok": True, "files": contents, "sha256": hashes,
                "verification_scope": "file_integrity_only", "tested_targets": [],
                "tests_passed": None}

    def extract_verified_artifact(self, arguments, result):
        # Result is produced by this tool, not supplied as model arguments.
        return {"kind": "file", "content": json.dumps(result["files"], ensure_ascii=False),
                "file_sha256": result["sha256"], "tested_targets": [], "tests_passed": None,
                "verification_scope": "file_integrity_only", "completes_branch": True}


"""Batch-envelope apply_patch: one call can carry multiple file ops (Update/Add/
Delete/Move) with @@-anchored hunks. Strict context matching; ambiguous hunks are
rejected with precise errors. Legacy old_text/new_text mode still supported."""
from typing import Any


class ApplyPatchTool:
    """Context-anchored patch: apply a targeted edit with verification.

    Use this for precise, minimal edits: provide the exact current text
    (old_text) and the replacement (new_text). The tool verifies the old
    lines match before applying. Returns the diff on success, or the
    mismatch on failure.
    """

    name = "apply_patch"
    parallel_safe = False
    read_only = False
    speculation_safe = False

    def __init__(self, workspace: WorkspaceAccess):
        self.workspace = workspace

    def schema(self) -> dict[str, Any]:
        return _schema(
            self.name,
            "Apply a context-anchored patch to a file. The patch must include "
            "the old lines (with -) and new lines (with +). The old lines must "
            "exactly match the current file content at the target location. "
            "Use this for precise, minimal edits instead of rewriting entire files.",
            {
                "path": {"type": "string", "description": "File path in workspace"},
                "old_text": {
                    "type": "string",
                    "description": "The exact text to find and replace (must match current content)",
                },
                "new_text": {
                    "type": "string",
                    "description": "The replacement text",
                },
            },
            ["path", "old_text", "new_text"],
        )

    def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        import difflib
        path = arguments.get("path", "")
        old_text = arguments.get("old_text", "")
        new_text = arguments.get("new_text", "")

        try:
            file_path = self.workspace.resolve(path)
        except Exception as e:
            return {"error": f"Cannot resolve path: {e}"}

        if not file_path.exists():
            return {"error": f"File not found: {path}"}

        try:
            current = file_path.read_text(encoding="utf-8")
        except Exception as e:
            return {"error": f"Cannot read file: {e}"}

        if old_text not in current:
            # Show nearby content to help agent find the right context
            best_ratio = 0
            best_line = ""
            for i in range(len(current)):
                chunk = current[i:i + len(old_text)]
                ratio = difflib.SequenceMatcher(None, old_text, chunk).ratio()
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_line = current[max(0, i-20):i+len(old_text)+20]
            return {
                "error": "old_text not found in file",
                "hint": f"Best match ({best_ratio:.0%} similar): ...{best_line[:100]}...",
                "suggestion": "Re-read the file and use the exact current content as old_text.",
            }

        # Apply the patch
        new_content = current.replace(old_text, new_text, 1)

        try:
            file_path.write_text(new_content, encoding="utf-8")
        except Exception as e:
            return {"error": f"Cannot write file: {e}"}

        # The agent now owns this file's content: later write_file overwrites are allowed.
        self.workspace.authored_paths.add(str(file_path))

        # Return the diff
        diff = list(difflib.unified_diff(
            old_text.splitlines(keepends=True),
            new_text.splitlines(keepends=True),
            fromfile=path,
            tofile=path,
        ))
        return {
            "status": "ok",
            "path": path,
            "diff": "".join(diff[:50]),
        }

    def speculation_snapshot(self, arguments: dict[str, Any]) -> str:
        return self.workspace.snapshot_token(arguments.get("path", ""))


def build_workspace_tools(root: Path) -> list[Any]:
    workspace = WorkspaceAccess(root)
    return [
        ReadFileTool(workspace),
        ListFilesTool(workspace),
        SearchTextTool(workspace),
        WriteFileTool(workspace),
        WriteFileChunkTool(workspace),
        ApplyPatchTool(workspace),
        ReportFrontierStateTool(),
        DeliverFrontierReportTool(workspace),
        DeliverFilesTool(workspace),
    ]


def _schema(
    name: str,
    description: str,
    properties: dict[str, Any],
    required: list[str],
) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
                "additionalProperties": False,
            },
        },
    }
