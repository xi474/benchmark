"""Bounded Runtime-owned state for online parallel-readiness prediction.

The executor may report a small semantic delta on each model turn.  Those
claims are advisory.  Durable completion/read/write facts are derived only
from real tool results, deduplicated by path and content digest, and exposed to
the classifier at the next request boundary.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
import shlex
from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import Any

from .dynamic_frontier import (
    build_dynamic_frontier, canonical_work_unit_id, _path as normalize_workspace_path,
    g1_enabled, MAX_FRONTIER_CANDIDATES,
    _delivered_paths, _is_completed, _safe_workspace_path,
    _materialized_writes, _materialized_step, _repair_is_justified,
)


from .g1_discovery import contract_heuristics_enabled


MAX_CONTENT_CHARS = 2400
MAX_ITEMS_PER_GROUP = 10
MAX_RECENT_COMMANDS = 4
MAX_FAILURES = 4
MAX_DISCOVERED_INPUTS = 96


def is_contract_path(value: Any) -> bool:
    """Return whether a workspace path is likely to define a shared interface.

    This is intentionally a path-level control hint, not a task DAG.  Reading a
    matching file never proves that the contract is usable; Runtime separately
    tracks materialization and validation below.
    """

    path = _path(value).lower()
    if not path:
        return False
    name = PurePosixPath(path).name
    stem = PurePosixPath(path).stem
    exact = {
        "contract.json", "contracts.json", "schema.json", "schemas.json",
        "interface.json", "interfaces.json", "protocol.json", "protocols.json",
        "manifest.json", "task.md", "spec.md", "requirements.md",
    }
    tokens = {"contract", "contracts", "schema", "schemas", "interface", "interfaces", "protocol", "protocols"}
    return (name in exact or name.startswith("readme")
            or any(token in tokens for token in stem.replace("-", "_").split("_")))


def is_validation_command(value: Any) -> bool:
    """Recognize a validator invocation whose status can establish success."""
    command = str(value or "")
    if "\n" in command or "\r" in command:
        return False
    lexer = shlex.shlex(command, posix=False, punctuation_chars=";&|()<>")
    lexer.whitespace_split = True
    try:
        words = list(lexer)
    except ValueError:
        return False
    # A pipeline, fallback, or later unconditional command can mask failure.
    segments: list[list[str]] = [[]]
    for word in words:
        if word == "&&":
            segments.append([])
        elif word[0] in ";&|()":
            return False
        else:
            segments[-1].append(word.strip("'\""))
    return any(_is_validation_invocation(segment) for segment in segments)


def _is_validation_invocation(words: list[str]) -> bool:
    if not words:
        return False
    program = PurePosixPath(words[0].replace("\\", "/")).name.lower().removesuffix(".exe")
    args = words[1:]
    if program == "timeout":
        duration = next((i for i, arg in enumerate(args) if re.fullmatch(r"\d+(?:\.\d+)?[smhd]?", arg)), None)
        return duration is not None and _is_validation_invocation(args[duration + 1:])
    if any(arg in {"-h", "-V", "-VV", "--help", "--version", "--collect-only", "--co", "--fixtures"} for arg in args):
        return False
    runners = {"pytest", "py.test", "unittest", "compileall", "mypy"}
    if program in runners:
        return True
    if re.fullmatch(r"(?:python(?:\d+(?:\.\d+)?)?|py)", program):
        while args and args[0].startswith("-") and not args[0].startswith(("-m", "-c")) and args[0] != "-":
            flag = args.pop(0)
            if flag in {"-X", "-W"} and args:
                args.pop(0)
        if args[:1] == ["-m"]:
            return len(args) > 1 and args[1] in runners
        if args and args[0].startswith("-m"):
            return args[0][2:] in runners
        if not args or args[0].startswith("-"):
            return False
        program = PurePosixPath(args[0].replace("\\", "/")).name.lower()
        args = args[1:]
    if program == "visible_contract_check_sdk.py":
        return "--unittest" in args
    if (program in {"check.py", "check_module.py", "verifier_checks.py", "smoke_test.py"}
            or program.endswith(".py") and (program.startswith("test_") or program.endswith("_test.py"))):
        return True
    return (
        program in {"npm", "pnpm", "yarn", "cargo", "go", "mvn", "gradle"} and args[:1] == ["test"]
        or program == "npm" and args[:2] == ["run", "build"]
        or program in {"pnpm", "yarn"} and args[:1] == ["build"]
        or program == "ruff" and args[:1] == ["check"]
    )


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _text(value: Any, limit: int = MAX_CONTENT_CHARS) -> str:
    return " ".join(str(value or "").split())[:limit]


def _path(value: Any) -> str:
    return normalize_workspace_path(value)


def _read_group(path: str) -> str:
    lower = path.lower()
    name = PurePosixPath(lower).name
    if (name.startswith("readme") or name in {"check.py", "contract.json", "schema.json"}
            or any(token in lower for token in ("spec", "contract", "requirement", "instruction"))):
        return "contract_reads"
    parts = set(PurePosixPath(lower).parts)
    if parts.intersection({"input", "inputs", "data", "dataset", "fixtures", "fixture"}):
        return "input_reads"
    if PurePosixPath(lower).suffix in {".csv", ".tsv", ".json", ".jsonl", ".yaml", ".yml", ".parquet"}:
        return "input_reads"
    if PurePosixPath(lower).suffix in {
        ".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".go", ".rs",
        ".cpp", ".c", ".h", ".bas", ".cls", ".frm",
    }:
        return "source_reads"
    return "other_reads"


_SHELL_READ_SUFFIXES = (
    "md", "txt", "json", "jsonl", "yaml", "yml", "csv", "tsv",
    "py", "js", "jsx", "ts", "tsx", "java", "go", "rs", "cpp", "c", "h",
    "bas", "cls", "frm", "frx", "sh", "toml", "ini", "cfg",
)
_SHELL_PATH_PATTERN = re.compile(
    r"(?P<path>(?:/[A-Za-z0-9_.@+*\-]+(?:/[A-Za-z0-9_.@+*\-]+)*|"
    r"(?:[A-Za-z0-9_.@+*\-]+/)*[A-Za-z0-9_.@+*\-]+)\."
    r"(?:" + "|".join(sorted(_SHELL_READ_SUFFIXES, key=len, reverse=True)) + r"))(?![A-Za-z0-9])",
    flags=re.IGNORECASE,
)


def shell_read_paths(command: Any) -> list[str]:
    """Infer files actually exposed by a successful shell read command.

    The shell tool is real verified evidence, but earlier memory code treated
    every shell result as an opaque command.  This conservative parser only
    recognizes file-like arguments in commands containing common read verbs;
    it does not infer task dependencies or completion.
    """

    text = str(command or "")
    # Variables/substitutions are expanded by the shell, not by this observer.
    # Their concrete output may establish inventory, never invented full reads.
    if "$" in text or "`" in text:
        return []
    if not re.search(r"\b(cat|head|tail|sed|grep|findstr|type|open|read_text)\b", text, re.I):
        return []
    bases = re.findall(r"(?:^|[;&|]\s*)cd\s+['\"]?([^\s;&|\"']+)", text, re.I)
    base = _path(bases[-1]) if bases else ""
    values: list[str] = []
    for match in _SHELL_PATH_PATTERN.finditer(text):
        raw_path = match.group("path")
        if any(c in raw_path for c in "*?[]{}"):
            continue
        absolute = raw_path.startswith("/")
        path = _path(raw_path)
        if not path:
            continue
        # A path immediately following a redirect is an output, not a read.
        prefix = text[max(0, match.start() - 3):match.start()]
        if ">" in prefix:
            continue
        if not absolute and base:
            path = f"{base.rstrip('/')}/{path}"
        if path not in values:
            values.append(path)
    return values[:16]


def shell_inventory_paths(command: Any, output: Any) -> list[str]:
    """Extract concrete file inventory facts from a successful shell result.

    Unlike ``shell_read_paths``, this does not claim file contents were read.
    It only records that a path was exposed by the command or its output.  This
    lets Runtime discover independent source surfaces after ``find``/``wc``
    without treating an inventory listing as completed investigation.
    """

    command_text = str(command or "")
    output_text = str(output or "")
    bases = re.findall(
        r"(?:^|[;&|]\s*)cd\s+['\"]?([^\s;&|\"']+)", command_text, re.I
    )
    base = _path(bases[-1]) if bases else ""
    values: list[str] = []
    command_literals = "" if "$" in command_text or "`" in command_text else command_text
    for text in (command_literals, output_text):
        for match in _SHELL_PATH_PATTERN.finditer(text):
            raw_path = match.group("path")
            if any(c in raw_path for c in "*?[]{}") or (
                match.start() and text[match.start()-1] in "$}`"
            ):
                continue
            absolute = raw_path.startswith("/")
            path = _path(raw_path)
            if not path:
                continue
            if not absolute and base:
                path = f"{base.rstrip('/')}/{path}"
            if path not in values:
                values.append(path)
    return values[:MAX_DISCOVERED_INPUTS]


def shell_read_level(command: Any) -> str:
    """Conservatively grade a shell content read as partial or full."""

    text = " ".join(str(command or "").lower().split())
    if re.search(r"\b(head|tail|sed|grep|findstr)\b", text):
        return "partial"
    if re.search(r"\b(cat|type|read_text)\b", text):
        return "full"
    return "partial"


def _ok(result: Any) -> bool:
    if not isinstance(result, dict):
        return False
    if result.get("ok") is False:
        return False
    return result.get("returncode", 0) == 0


def compact_tool_delta(rows: list[dict[str, Any]], limit: int = 6) -> list[dict[str, Any]]:
    """Represent the newest change without duplicating content already in memory."""
    compact: list[dict[str, Any]] = []
    for row in rows[-limit:]:
        tool = str(row.get("tool", ""))
        args = row.get("arguments") if isinstance(row.get("arguments"), dict) else {}
        result = row.get("result") if isinstance(row.get("result"), dict) else {}
        item: dict[str, Any] = {"tool": tool, "ok": _ok(result)}
        path = _path(result.get("path") or args.get("path"))
        if path:
            item["path"] = path
        if tool == "read_file":
            content = str(result.get("content", ""))
            item["content_sha256"] = hashlib.sha256(content.encode("utf-8")).hexdigest()
            item["chars"] = result.get("chars", len(content))
        elif tool == "list_files":
            entries = result.get("entries") if isinstance(result.get("entries"), list) else []
            item["entries"] = [entry.get("path") for entry in entries[:24] if isinstance(entry, dict)]
        elif tool in {"write_file", "edit_file", "apply_patch"}:
            item["chars_written"] = result.get("chars_written")
        elif tool == "shell":
            item.update(command=_text(args.get("command"), 320),
                        returncode=result.get("returncode", 0),
                        output_excerpt=str(result.get("output", ""))[-600:])
        else:
            item["arguments"] = json.loads(_canonical(args)[:1200]) if len(_canonical(args)) <= 1200 else _text(args, 1200)
            item["result_excerpt"] = _text(result, 1200)
        compact.append(item)
    return compact


def _bounded_values(mapping: dict[str, dict[str, Any]], limit: int = MAX_ITEMS_PER_GROUP) -> list[dict[str, Any]]:
    rows = sorted(mapping.values(), key=lambda row: (row.get("last_step", -1), row.get("key", "")))
    public = []
    for row in sorted(rows[-limit:], key=lambda item: item.get("key", "")):
        value = {key: copy.deepcopy(item) for key, item in row.items()
                 if key not in {"key", "last_step", "evidence_id"}}
        public.append(value)
    return public


def _public_events(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {key: copy.deepcopy(value) for key, value in row.items()
         if key not in {"key", "last_step", "evidence_id"}}
        for row in rows
    ]


def _bounded_discovered_values(
    mapping: dict[str, dict[str, Any]], limit: int = MAX_DISCOVERED_INPUTS
) -> list[dict[str, Any]]:
    """Bound discovered artifacts while retaining their audit provenance."""

    rows = sorted(
        mapping.values(), key=lambda row: (row.get("last_step", -1), row.get("key", ""))
    )[-limit:]
    return [
        {
            key: copy.deepcopy(value)
            for key, value in row.items()
            if key not in {"key", "last_step"}
        }
        for row in sorted(rows, key=lambda item: item.get("key", ""))
    ]


@dataclass
class RuntimeClassifierState:
    """Accumulate only compact decision facts, never replay full history."""

    seen_evidence_ids: set[str] = field(default_factory=set)
    reads: dict[str, dict[str, dict[str, Any]]] = field(default_factory=lambda: {
        "contract_reads": {}, "input_reads": {}, "source_reads": {}, "other_reads": {},
    })
    writes: dict[str, dict[str, Any]] = field(default_factory=dict)
    deliveries: dict[str, dict[str, Any]] = field(default_factory=dict)
    recent_commands: list[dict[str, Any]] = field(default_factory=list)
    validation_checks: dict[str, dict[str, Any]] = field(default_factory=dict)
    failures: list[dict[str, Any]] = field(default_factory=list)
    inventories: dict[str, dict[str, Any]] = field(default_factory=dict)
    discovered_inputs: dict[str, dict[str, Any]] = field(default_factory=dict)
    llm_done_claims: dict[str, str] = field(default_factory=dict)
    llm_ready_claims: dict[str, dict[str, Any]] = field(default_factory=dict)
    llm_blocked_claims: dict[str, str] = field(default_factory=dict)
    llm_active_claims: dict[str, str] = field(default_factory=dict)
    consumed_delta_ids: set[str] = field(default_factory=set)
    latest_delta: dict[str, Any] | None = None
    latest_phase: str = "inspect"
    last_update_step: int = 0

    def _remember_discovered_input(
        self,
        path: Any,
        *,
        evidence_id: str,
        step: int,
        observation_level: str = "inventory",
    ) -> None:
        normalized = _path(path)
        if not normalized:
            return
        key = normalized.lower()
        levels = {"inventory": 0, "partial": 1, "full": 2}
        previous = self.discovered_inputs.get(key, {})
        previous_level = str(previous.get("observation_level", "inventory"))
        if levels.get(observation_level, 0) < levels.get(previous_level, 0):
            observation_level = previous_level
        self.discovered_inputs[key] = {
            "key": key,
            "path": normalized,
            "observation_level": observation_level,
            "evidence_id": evidence_id,
            "last_step": step,
        }
        if len(self.discovered_inputs) > MAX_DISCOVERED_INPUTS:
            oldest = sorted(
                self.discovered_inputs,
                key=lambda item: self.discovered_inputs[item].get("last_step", -1),
            )[: len(self.discovered_inputs) - MAX_DISCOVERED_INPUTS]
            for item in oldest:
                self.discovered_inputs.pop(item, None)

    def merge_observations(self, observations: tuple[dict[str, Any], ...] | list[dict[str, Any]], step: int) -> list[dict[str, Any]]:
        """Validate and merge only observations not consumed at an earlier boundary."""
        new_rows: list[dict[str, Any]] = []
        for raw in observations:
            evidence_id = str(raw.get("evidence_id", ""))
            if not evidence_id or evidence_id in self.seen_evidence_ids:
                continue
            self.seen_evidence_ids.add(evidence_id)
            row = copy.deepcopy(raw)
            new_rows.append(row)
            tool = str(row.get("tool", ""))
            args = row.get("arguments") if isinstance(row.get("arguments"), dict) else {}
            result = row.get("result") if isinstance(row.get("result"), dict) else {}
            if not _ok(result):
                self.failures.append({
                    "tool": tool, "path": _path(args.get("path") or result.get("path")),
                    "evidence_id": evidence_id, "result": copy.deepcopy(result), "last_step": step,
                })
                self.failures = self.failures[-MAX_FAILURES:]
                continue

            if tool == "report_frontier_state":
                delta = result.get("delta")
                if isinstance(delta, dict):
                    # The tool schema and execute path have already bounded the
                    # payload.  Treat it as advisory LLM state, keyed by the
                    # real tool-result evidence id so retries deduplicate.
                    self.merge_llm_deltas(
                        [{
                            "delta_id": f"tool:{evidence_id}",
                            "reported_at_step": step,
                            "delta": delta,
                        }],
                        step,
                    )
            elif tool == "read_file":
                path = _path(result.get("path") or args.get("path"))
                content = str(result.get("content", ""))
                if path:
                    group = _read_group(path)
                    key = path.lower()
                    self.reads[group][key] = {
                        "key": key, "path": path,
                        "content_sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
                        "content_excerpt": content[:MAX_CONTENT_CHARS],
                        "truncated": len(content) > MAX_CONTENT_CHARS or bool(result.get("truncated")),
                        "evidence_id": evidence_id, "last_step": step,
                    }
                    self._remember_discovered_input(
                        path,
                        evidence_id=evidence_id,
                        step=step,
                        observation_level=(
                            "partial"
                            if len(content) > MAX_CONTENT_CHARS or bool(result.get("truncated"))
                            else "full"
                        ),
                    )
            elif tool == "list_files":
                path = _path(args.get("path")) or "."
                entries = result.get("entries") if isinstance(result.get("entries"), list) else []
                self.inventories[path] = {
                    "key": path, "path": path,
                    "entries": [copy.deepcopy(item) for item in entries[:24]],
                    "truncated": len(entries) > 24 or bool(result.get("truncated")),
                    "evidence_id": evidence_id, "last_step": step,
                }
                for item in entries:
                    if not isinstance(item, dict):
                        continue
                    entry_path = item.get("path") or item.get("name")
                    if entry_path and not str(entry_path).startswith("/") and path not in {"", "."}:
                        entry_path = f"{path.rstrip('/')}/{str(entry_path).lstrip('/')}"
                    self._remember_discovered_input(
                        entry_path,
                        evidence_id=evidence_id,
                        step=step,
                    )
            elif tool in {"write_file", "write_file_chunk", "edit_file", "apply_patch"}:
                path = _path(result.get("path") or args.get("path"))
                if path:
                    content = args.get("content", args.get("patch", ""))
                    self.writes[path.lower()] = {
                        "key": path.lower(), "path": path, "tool": tool,
                        "content_sha256": hashlib.sha256(str(content).encode("utf-8")).hexdigest(),
                        "evidence_id": evidence_id, "last_step": step,
                    }
                    self._remember_discovered_input(
                        path,
                        evidence_id=evidence_id,
                        step=step,
                        observation_level="full",
                    )
            elif tool in {"deliver_files", "deliver_frontier_report"}:
                delivery_key = evidence_id
                self.deliveries[delivery_key] = {
                    "key": delivery_key, "arguments": copy.deepcopy(args),
                    "result": copy.deepcopy(result), "evidence_id": evidence_id, "last_step": step,
                }
            elif tool in {"choose_execution_mode_v2", "spawn_subtasks"}:
                # Parent scopes receive one joined plan result, not each child's
                # tool messages. Promote Runtime-attested materialized paths into
                # durable state; never copy the large nested branch payload. This
                # includes implementation deliveries so a completed frontend or
                # backend is not offered again immediately after its join.
                encoded = json.dumps(result, ensure_ascii=False)
                paths = set(
                    match.group(0).removeprefix("/workspace/")
                    for match in re.finditer(
                        r"(?:/workspace/)?\.semserve/frontier/[A-Za-z0-9_.-]+\.json",
                        encoded,
                    )
                )
                joined_rows: list[dict[str, Any]] = []
                for key in ("subtasks", "artifacts"):
                    value = result.get(key)
                    if isinstance(value, list):
                        joined_rows.extend(
                            item for item in value if isinstance(item, dict)
                        )
                for item in joined_rows:
                    artifact = item.get("artifact")
                    artifact = artifact if isinstance(artifact, dict) else item
                    if artifact.get("delivery_verified") is not True:
                        continue
                    materialized = artifact.get("materialized_files")
                    if not isinstance(materialized, dict):
                        continue
                    for raw_path in materialized:
                        path = _path(raw_path)
                        if path.startswith("workspace/"):
                            path = path.removeprefix("workspace/")
                        if path:
                            paths.add(path)
                paths = sorted(paths)
                if paths:
                    # A Runtime-attested child delivery is stronger than a
                    # parent directory listing: the artifact exists and its
                    # content was validated at join.  Promote it as a fully
                    # observed parent input so successor read_sets can refer to
                    # real joined outputs without forcing redundant rereads.
                    for path in paths:
                        self._remember_discovered_input(
                            path,
                            evidence_id=evidence_id,
                            step=step,
                            observation_level="full",
                        )
                    delivery_key = evidence_id
                    self.deliveries[delivery_key] = {
                        "key": delivery_key,
                        "source_tool": tool,
                        "verified_artifact_paths": paths,
                        "evidence_id": evidence_id,
                        "last_step": step,
                    }
            elif tool == "shell":
                if contract_heuristics_enabled():
                    # Exact labelled JSON blocks are content reads. Unlabelled
                    # loops/listings remain inventory; never guess their paths.
                    from .g1_discovery import contract_read_observations
                    for observed in contract_read_observations([row]):
                        path = _path(observed["path"])
                        key = path.casefold()
                        content = observed["content"]
                        derived_id = observed["evidence_id"]
                        self.seen_evidence_ids.add(derived_id)
                        self.reads["contract_reads"][key] = {
                            "key": key, "path": path,
                            "content_sha256": observed["content_sha256"],
                            "content_excerpt": content[:MAX_CONTENT_CHARS],
                            "truncated": len(content) > MAX_CONTENT_CHARS,
                            "provenance": observed["provenance"],
                            "source_evidence_id": observed["source_evidence_id"],
                            "evidence_id": derived_id, "last_step": step,
                        }
                        self._remember_discovered_input(
                            path, evidence_id=derived_id, step=step, observation_level="full")
                        self.discovered_inputs[key]["source_evidence_id"] = observed["source_evidence_id"]
                command = _text(args.get("command"), 320)
                output = str(result.get("output", ""))
                command_row = {
                    "key": _digest([command, result.get("returncode", 0), output]),
                    "command": command,
                    "returncode": result.get("returncode", 0),
                    "output_excerpt": output[-800:],
                    "evidence_id": evidence_id, "last_step": step,
                }
                # Re-running an identical successful check is not new task
                # progress. Keep only its newest occurrence for bounded input.
                self.recent_commands = [
                    item for item in self.recent_commands
                    if item.get("key") != command_row["key"]
                ]
                self.recent_commands.append(command_row)
                self.recent_commands = self.recent_commands[-MAX_RECENT_COMMANDS:]
                for path in shell_inventory_paths(args.get("command"), output):
                    self._remember_discovered_input(
                        path,
                        evidence_id=evidence_id,
                        step=step,
                    )
                read_level = shell_read_level(args.get("command"))
                for path in shell_read_paths(args.get("command")):
                    group = _read_group(path)
                    key = path.lower()
                    self.reads[group][key] = {
                        "key": key,
                        "path": path,
                        "content_sha256": hashlib.sha256(output.encode("utf-8")).hexdigest(),
                        "content_excerpt": output[:MAX_CONTENT_CHARS],
                        "truncated": len(output) > MAX_CONTENT_CHARS,
                        "provenance": "verified_shell_read",
                        "evidence_id": evidence_id,
                        "last_step": step,
                    }
                    self._remember_discovered_input(
                        path,
                        evidence_id=evidence_id,
                        step=step,
                        observation_level=read_level,
                    )
                if is_validation_command(args.get("command")):
                    self.validation_checks[command] = copy.deepcopy(command_row)
        if new_rows:
            self.last_update_step = step
        return new_rows

    def merge_llm_deltas(self, deltas: list[dict[str, Any]], current_step: int) -> None:
        """Merge schema-valid reports available by this boundary as advisory state."""
        for envelope in deltas:
            if int(envelope.get("reported_at_step", current_step)) > current_step:
                continue
            delta_id = str(envelope.get("delta_id", ""))
            if not delta_id or delta_id in self.consumed_delta_ids:
                continue
            delta = envelope.get("delta")
            if not isinstance(delta, dict):
                continue
            self.consumed_delta_ids.add(delta_id)
            self.latest_delta = copy.deepcopy(delta)
            self.latest_phase = str(delta.get("phase", self.latest_phase))
            for value in delta.get("done_add", []):
                text = _text(value, 160)
                if text:
                    self.llm_done_claims[_digest(text)] = text
            for value in delta.get("blocked_add", []):
                text = _text(value, 160)
                if text:
                    self.llm_blocked_claims[_digest(text)] = text
            for value in delta.get("active_add", []):
                text = _text(value, 160)
                if text:
                    self.llm_active_claims[_digest(text)] = text
            for value in delta.get("active_remove", []):
                text = _text(value, 160)
                if text:
                    self.llm_active_claims.pop(_digest(text), None)
            for item in delta.get("ready_upsert", []):
                if not isinstance(item, dict):
                    continue
                goal = _text(item.get("goal"), 160)
                if goal:
                    work_unit_id = canonical_work_unit_id(item.get("work_unit_id"))
                    key = _digest(work_unit_id or goal)
                    stored = copy.deepcopy(item)
                    if work_unit_id:
                        stored["work_unit_id"] = work_unit_id
                    if g1_enabled():
                        self.llm_ready_claims.pop(key, None)
                    self.llm_ready_claims[key] = stored
            for value in delta.get("ready_remove", []):
                goal = _text(value, 160)
                if goal:
                    self.llm_ready_claims.pop(_digest(goal), None)
                    canonical_id = canonical_work_unit_id(goal)
                    if canonical_id:
                        self.llm_ready_claims.pop(_digest(canonical_id), None)
                    for key, item in list(self.llm_ready_claims.items()):
                        if (goal == _text(item.get("goal"), 160) or (
                            item.get("work_unit_id") and canonical_id
                            == canonical_work_unit_id(item["work_unit_id"])
                        )):
                            self.llm_ready_claims.pop(key, None)
        if deltas:
            self.last_update_step = max(self.last_update_step, current_step)

    def snapshot(self, task: str = "") -> dict[str, Any]:
        reads = {name: _bounded_values(values) for name, values in self.reads.items()}
        contract_reads = [
            item for item in self.reads["contract_reads"].values()
            if is_contract_path(item.get("path"))
        ]
        contract_writes = [
            item for item in self.writes.values()
            if is_contract_path(item.get("path"))
        ]
        last_contract_step = max(
            (int(item.get("last_step", -1)) for item in contract_reads + contract_writes),
            default=-1,
        )
        later_validations = [
            item for item in self.validation_checks.values()
            if int(item.get("last_step", -1)) >= last_contract_step >= 0
        ]
        if contract_writes and later_validations:
            contract_status = "verified_after_write"
        elif contract_writes:
            contract_status = "materialized_unverified"
        elif contract_reads and later_validations:
            contract_status = "verified_existing"
        elif contract_reads:
            contract_status = "observed_unverified"
        else:
            contract_status = "unseen"
        tool_state = {
            **reads,
            "workspace_inventory": _bounded_values(self.inventories, 3),
            "discovered_input_artifacts": _bounded_discovered_values(
                self.discovered_inputs, MAX_DISCOVERED_INPUTS
            ),
            # Keep enough distinct artifact paths for durable surface state.
            # Ten recent frontend writes previously evicted earlier backend
            # evidence and made a completed surface appear ready again.
            "written_artifacts": _bounded_values(self.writes, 48),
            "branch_deliveries": _bounded_values(self.deliveries, 6),
            "recent_successful_commands": _public_events(self.recent_commands),
            "successful_validation_checks": _bounded_values(self.validation_checks, 4),
            "recent_failures": _public_events(self.failures),
            "unique_evidence_count": len(self.seen_evidence_ids),
        }
        contract_state = {
            "status": contract_status,
            "contract_ready": contract_status in {"verified_after_write", "verified_existing"},
            "read_paths": sorted({item["path"] for item in contract_reads}),
            "materialized_paths": sorted({item["path"] for item in contract_writes}),
            "validation_commands": sorted({item["command"] for item in later_validations}),
            "last_contract_step": last_contract_step if last_contract_step >= 0 else None,
        }
        ready_claims = list(self.llm_ready_claims.values())[-8:]
        if g1_enabled():
            delivered = _delivered_paths(tool_state)
            materialized = _materialized_writes({"written_artifacts": list(self.writes.values())})
            pending = []
            completed = []
            for item in self.llm_ready_claims.values():
                contract = item.get("completion_contract") or {}
                paths = [path for value in contract.get("required_artifact_paths", [])
                         if (path := _safe_workspace_path(value))]
                if _is_completed(paths, delivered):
                    completed.append(item)
                    continue
                last_write = _materialized_step(paths, materialized)
                if last_write is not None and not _repair_is_justified(
                    kind=str(item.get("kind") or ""), goal=str(item.get("goal") or ""),
                    materialized_step=last_write, failures=self.failures,
                    owned_paths=list(item.get("write_set") or []),
                ):
                    completed.append(item)
                    continue
                pending.append(item)
            # Completed reports cannot evict an older still-pending candidate.
            # Only the published view is bounded; canonical pending IDs remain
            # in the cumulative cache and are re-evaluated on later evidence.
            capacity = MAX_FRONTIER_CANDIDATES * 4
            retained = pending[-capacity:]
            spare = capacity - len(retained)
            # Keep recent completed claims for the existing advisory/rejection
            # feedback when space permits, but never ahead of live candidates.
            ready_claims = (completed[-spare:] if spare else []) + retained
        llm_state = {
            "authority": "advisory_unverified",
            "phase": self.latest_phase,
            "done_claims": list(self.llm_done_claims.values())[-8:],
            "ready_claims": ready_claims,
            "blocked_claims": list(self.llm_blocked_claims.values())[-6:],
            "active_claims": list(self.llm_active_claims.values())[-6:],
            "latest_delta": copy.deepcopy(self.latest_delta),
        }
        # Keep chronology for control without publishing step counters in the
        # compact predictor snapshot.
        frontier_tool_state = {
            **tool_state,
            "written_artifacts": [
                {**item, "last_step": self.writes[item["path"].lower()]["last_step"]}
                for item in tool_state["written_artifacts"]
            ],
            "recent_failures": self.failures,
        }
        frontier = build_dynamic_frontier(
            task,
            contract_state,
            frontier_tool_state,
            llm_state,
            step=self.last_update_step,
        )
        return {
            "schema_version": "semserve.cumulative-verified-state.v2",
            "last_update_step": self.last_update_step,
            "verified_tool_state": tool_state,
            "verified_contract_state": contract_state,
            "llm_reported_state": llm_state,
            "dynamic_frontier": frontier,
        }

    def predictor_views(self, task: str = "") -> tuple[dict[str, Any], list[dict[str, Any]]]:
        """Return compact state plus cumulative facts in the proven tool-evidence shape.

        Read content appears exactly once, in the evidence list.  The structured
        state retains hashes and paths for control/audit without duplicating text.
        """
        state = self.snapshot(task)
        evidence: list[dict[str, Any]] = []
        tool_state = state["verified_tool_state"]
        for group in ("contract_reads", "input_reads", "source_reads", "other_reads"):
            for item in tool_state[group]:
                content = item.pop("content_excerpt", "")
                evidence.append({
                    "tool": "read_file",
                    "arguments": {"path": item["path"]},
                    "result": {
                        "ok": True,
                        "path": item["path"],
                        "content": content,
                        "truncated": item.get("truncated", False),
                    },
                })
        for item in tool_state["written_artifacts"]:
            evidence.append({
                "tool": item.get("tool", "write_file"),
                "arguments": {"path": item["path"]},
                "result": {"ok": True, "path": item["path"]},
            })
        for item in tool_state["recent_successful_commands"]:
            evidence.append({
                "tool": "shell",
                "arguments": {"command": item.get("command", "")},
                "result": {"ok": item.get("returncode", 1) == 0,
                           "returncode": item.get("returncode"),
                           "output": item.get("output_excerpt", "")},
            })
        for item in tool_state["recent_failures"]:
            evidence.append({
                "tool": item.get("tool", "unknown"),
                "arguments": {"path": item.get("path", "")},
                "result": copy.deepcopy(item.get("result", {})),
            })
        return state, evidence

