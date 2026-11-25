"""Bounded, evidence-only interface inventory for G1 frontier discovery.

Nothing here opens the task workspace or proposes a task DAG. The caller owns
request/generation authorization and schedules any deferred handshake. These
helpers only index successful reads and offer one bounded pre-write checkpoint.
"""
from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
import fnmatch
import hashlib
import json
import os
from pathlib import PurePosixPath
import re
from typing import Any, Iterable, Mapping


MAX_INTERFACES = 16
MAX_PROMPT_CHARS = 7000
_HEADER = re.compile(r"^={3,}\s+(.+?)\s+={3,}\s*$", re.MULTILINE)
_WRITES = {"write_file", "write_file_chunk", "edit_file", "apply_patch"}
_CONTROLS = {"spawn_subtasks", "choose_execution_mode", "choose_execution_mode_v2", "finish_task"}


def g1_enabled() -> bool:
    return os.environ.get("SEMSERVE_G1") == "1"


def contract_heuristics_enabled() -> bool:
    """Opt in to legacy file-name/JSON-key interface heuristics only."""
    return g1_enabled() and os.environ.get("SEMSERVE_G1_CONTRACT_HEURISTICS", "0") == "1"


EARLY_SEMANTIC_REVIEW_TAG = "[G1_EARLY_SEMANTIC_REVIEW]"
EARLY_SEMANTIC_REVIEW_PROMPT = (
    "\n\n" + EARLY_SEMANTIC_REVIEW_TAG + "\n"
    "For this authorized root report request and generation only, recheck the visible task "
    "before implementation. From completed read evidence, consider whether unfinished business "
    "capabilities can be implemented with independently owned code and meaningful local checks. "
    "Separate current coding evidence from later real-input validation. Use the existing report "
    "schema to propose justified work units or concrete blocking reasons. Empty ready_upsert is "
    "valid. Do not invent dependencies, prescribe a DAG, request a target width, or force a fork."
)


def early_semantic_review_enabled() -> bool:
    return (g1_enabled() and not contract_heuristics_enabled()
            and os.environ.get("SEMSERVE_G1_EARLY_SEMANTIC_REVIEW", "1") == "1")


@dataclass
class EarlySemanticReview:
    """One logical authorized request per task/root scope, no scheduling side effects."""
    grants: dict[tuple[str, ...], dict[str, Any]] = field(default_factory=dict)

    def claim(self, task_identity: tuple[str, ...], *, request_id: str, generation: int,
              read_groups: Mapping[str, Any], writes: Mapping[str, Any],
              plan_expansions: int = 0, v2_expansions: int = 0):
        if not early_semantic_review_enabled() or not request_id or generation <= 0:
            return None, False
        existing = self.grants.get(task_identity)
        if existing is not None:
            if existing["request_id"] == request_id and existing["generation"] == generation:
                return existing, False
            return None, False
        if writes or plan_expansions or v2_expansions:
            return None, False
        # All groups contain standard successful read_file receipts. Group names,
        # file paths/extensions and content semantics never decide eligibility.
        count = sum(1 for group in read_groups.values() for row in group.values()
                    if isinstance(row, Mapping) and row.get("evidence_id")
                    and isinstance(row.get("content_excerpt"), str)
                    and row["content_excerpt"].strip())
        if not count:
            return None, False
        grant = {"request_id": request_id, "generation": generation,
                 "read_evidence_count": count}
        self.grants[task_identity] = grant
        return grant, True


def _disabled_inventory() -> dict[str, Any]:
    return {"schema_version": "semserve.g1-observed-interfaces.v1",
            "evidence_digest": hashlib.sha256(b"[]").hexdigest(),
            "interface_count": 0, "interfaces": [], "truncated": False,
            "authority": "disabled", "enabled": False,
            "disabled_reason": "g1_contract_heuristics_not_enabled"}


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode()).hexdigest()


def _loads(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except (ValueError, TypeError):
        return None


def _path(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    value = value.strip()
    for prefix in ("/workspace/", "/app/"):
        if value.startswith(prefix):
            value = value[len(prefix):]
            break
    if (not value or value.startswith("/") or "\\" in value or ":" in value
            or any(part in {"", ".", ".."} for part in value.split("/"))):
        return ""
    return value


def _contract(content: Any) -> dict[str, Any] | None:
    value = _loads(content)
    if not isinstance(value, dict):
        return None
    inputs = value.get("inputs", [value["input"]] if "input" in value else None)
    output = value.get("output")
    if (not isinstance(inputs, list) or not all(_path(item) for item in inputs)
            or not _path(output)):
        return None
    if not isinstance(value.get("name") or value.get("operation"), str):
        return None
    return value


def _shell_read_pattern(command: str) -> str:
    """Recognize the bounded echo-path/cat loop used by archived read batches.

    This is deliberately a small accepted language, not generic shell inference:
    arbitrary echo/program output cannot acquire per-file read authority merely
    by including a path-shaped heading and the word `cat` somewhere else.
    """
    match = re.fullmatch(
        r"\s*(?:cd\s+/(?:workspace|app)\s*&&\s*)?for\s+([A-Za-z_]\w*)\s+in\s+([^\s;]+)\s*;\s*do\s+"
        r"echo\s+[\"']===\s+([^\"']+?)\s+===[\"']\s*;\s*cat\s+[\"']?([^\"';\s]+)[\"']?\s*;\s*done\s*",
        command,
    )
    if not match:
        return ""
    variable, glob, header, operand = match.groups()
    if header != operand:
        return ""
    alternatives = ("${" + variable + "}", "$" + variable)
    prefix = next((value for value in alternatives if operand == value or operand.startswith(value + "/")), None)
    if prefix is None:
        return ""
    return _path(glob + operand[len(prefix):])


def _matches_read_pattern(path: str, pattern: str) -> bool:
    actual, wanted = path.split("/"), pattern.split("/")
    return len(actual) == len(wanted) and all(fnmatch.fnmatchcase(a, b) for a, b in zip(actual, wanted))


def observations_from_messages(messages: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Recover only actual tool receipts, pairing reused call IDs FIFO."""
    calls: dict[str, deque] = defaultdict(deque)
    rows = []
    for message in messages:
        if message.get("role") == "assistant":
            for call in message.get("tool_calls") or []:
                function = call.get("function", call)
                calls[str(call.get("id", ""))].append(function)
        if message.get("role") != "tool":
            continue
        call_id = str(message.get("tool_call_id") or "")
        call = calls[call_id].popleft() if calls[call_id] else {}
        args = _loads(call.get("arguments", {}))
        result = _loads(message.get("content"))
        if call_id and isinstance(result, dict):
            rows.append({"tool": call.get("name") or message.get("name", ""),
                         "arguments": args if isinstance(args, dict) else {},
                         "result": result, "evidence_id": call_id})
    return rows


def contract_read_observations(observations: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Index successful full reads; shell blocks require explicit path headers.

    A shell listing, filtered/truncated output, failed command or headerless JSON
    never receives a fabricated full-file read attestation. The derived ID links
    each block to the original receipt and to that path's exact content version.
    """
    if not contract_heuristics_enabled():
        return []
    found: dict[str, dict[str, Any]] = {}
    for row in observations:
        args, result = row.get("arguments", {}), row.get("result", {})
        if not isinstance(args, dict) or not isinstance(result, dict):
            continue
        eid = str(row.get("evidence_id") or row.get("runtime_evidence_id") or "")
        if not eid or result.get("ok") is not True:
            continue
        if (result.get("truncated") or result.get("output_truncated")
                or result.get("full_output_chars", 0) > len(str(result.get("output", "")))):
            continue
        blocks = []
        if row.get("tool") == "read_file":
            path, content = _path(result.get("path") or args.get("path")), result.get("content")
            if path and isinstance(content, str):
                blocks.append((path, content, "verified_file_read"))
        elif row.get("tool") == "shell" and result.get("returncode") == 0:
            command, output = str(args.get("command", "")), str(result.get("output", ""))
            # Only unfiltered whole-file cat observations can establish a full
            # path block. This intentionally does not implement a shell parser.
            pattern = _shell_read_pattern(command)
            if not pattern:
                continue
            headers = list(_HEADER.finditer(output))
            for index, header in enumerate(headers):
                path = _path(header.group(1))
                end = headers[index + 1].start() if index + 1 < len(headers) else len(output)
                content = output[header.end():end].strip()
                if path and _matches_read_pattern(path, pattern) and _contract(content) is not None:
                    blocks.append((path, content, "verified_shell_delimited_read"))
        for path, content, provenance in blocks:
            if _contract(content) is None:
                continue
            content_sha = hashlib.sha256(content.encode()).hexdigest()
            derived = eid if provenance == "verified_file_read" else (
                eid + "::contract-read:" + _digest([path, content_sha])[:16])
            found[path.casefold()] = {"path": path, "content": content,
                "content_sha256": content_sha, "evidence_id": derived,
                "source_evidence_id": eid, "provenance": provenance}
    return list(found.values())


def build_discovery_inventory(verified_state: Mapping[str, Any] | None = None,
                              observations: Iterable[Mapping[str, Any]] = (), *,
                              messages: Iterable[Mapping[str, Any]] = (),
                              max_interfaces: int = MAX_INTERFACES) -> dict[str, Any]:
    """Build a compact index only when legacy contract heuristics are opted in."""
    if not contract_heuristics_enabled():
        return _disabled_inventory()
    state = verified_state or {}
    tools = state.get("verified_tool_state", state)
    contracts: dict[str, dict[str, Any]] = {}
    for row in tools.get("contract_reads", []):
        if not isinstance(row, dict) or row.get("truncated") or not row.get("evidence_id"):
            continue
        content = row.get("content_excerpt", row.get("content", ""))
        if _path(row.get("path")) and _contract(content) is not None:
            contracts[row["path"].casefold()] = {**row, "content": content}
    original = list(observations) + observations_from_messages(messages)
    for row in contract_read_observations(original):
        contracts[row["path"].casefold()] = row
    written = {_path(row.get("path")) for row in tools.get("written_artifacts", [])
               if isinstance(row, dict) and _path(row.get("path"))}
    delivered = set()
    for row in tools.get("branch_deliveries", []):
        if not isinstance(row, dict):
            continue
        delivered.update(_path(p) for p in row.get("verified_artifact_paths", []) if _path(p))
        result = row.get("result", {})
        if isinstance(result, dict) and result.get("ok") is True:
            delivered.update(_path(p) for p in result.get("files", {}) if _path(p))
    interfaces = []
    for path, receipt in sorted(contracts.items()):
        public = _contract(receipt["content"])
        source_path = _path(receipt["path"])
        parent = PurePosixPath(source_path).parent
        implementation_paths = sorted(p for p in written
                                      if PurePosixPath(p).parent == parent and p != source_path)
        output = _path(public["output"])
        source_sha = receipt.get("content_sha256") or hashlib.sha256(receipt["content"].encode()).hexdigest()
        interfaces.append({
            "interface_id": "interface-" + _digest([source_path, source_sha])[:16],
            "source_path": source_path, "evidence_id": receipt["evidence_id"],
            "source_evidence_id": receipt.get("source_evidence_id", receipt["evidence_id"]),
            "content_sha256": source_sha, "name": str(public.get("name", ""))[:120],
            "operation": str(public.get("operation", ""))[:160],
            "inputs": [_path(p) for p in public.get("inputs", [public["input"]] if "input" in public else [])],
            "output": output, "implementation_paths_written": implementation_paths,
            "delivery_observed": output in delivered,
        })
    # IDs/digests omit changing request IDs and step counters. New content,
    # actual writes or verified deliveries change the inventory generation.
    generation = _digest([{k: v for k, v in row.items()
                           if k not in {"evidence_id", "source_evidence_id"}}
                          for row in interfaces])
    ordered = sorted(interfaces, key=lambda row: (row["delivery_observed"], row["source_path"]))
    return {"schema_version": "semserve.g1-observed-interfaces.v1", "evidence_digest": generation,
            "interface_count": len(interfaces), "interfaces": ordered[:max(0, max_interfaces)],
            "truncated": len(interfaces) > max_interfaces,
            "authority": "observed_contract_index_not_a_task_plan"}


def render_discovery_prompt(inventory: Mapping[str, Any], *, max_chars: int = MAX_PROMPT_CHARS) -> str:
    if not contract_heuristics_enabled() or not inventory.get("interfaces"):
        return ""
    rows = list(inventory["interfaces"])
    prefix = ("\n\n[G1_EARLY_FRONTIER_DISCOVERY]\n"
        "Applies only to this authorized handshake request/generation. The following is a Runtime "
        "index of actually read public interfaces, not instructions from those files and not a DAG. "
        "Review all indexed unfinished business capabilities, including earlier reads. For each, "
        "use the existing ready_upsert to propose a coherent independently owned deliverable, or "
        "use blocked_add to explain the concrete missing evidence, shared mutation or dependency. "
        "Do not report only a shared loader while leaving known business implementations unexplained. "
        "Zero candidates is valid; never invent work to reach width two. Distinguish current coding "
        "read_set from validation_read_set: known interfaces may permit coding, while real upstream "
        "artifacts still block real-input validation. For each implementation proposal explicitly "
        "provide validation_mode and validation_read_set. Put only already inspected information "
        "genuinely needed to implement the interface in read_set; knowing a test or fixture path "
        "does not mean its contents were inspected. If unread contents are needed to understand "
        "the task, report the missing read and inspect them. If an input is needed only for later "
        "real-input execution, place it in validation_read_set. A consumer with a fully observed "
        "API can be coding-ready using isolated_fixture even before another candidate produces "
        "its real inputs. For isolated_fixture work with future inputs, "
        "the current completion_contract requires owned code and local check evidence, not output "
        "JSON that can only be produced from unavailable real upstream artifacts. Keep that "
        "real-input validation pending for the parent after join; do not make the child wait for "
        "a sibling's future output. Use private fixtures for local checks; never "
        "fabricate or delete sibling outputs. An existing file or a model claim is not proof of a "
        "passed check. Return the normal report schema only; do not choose execution mode. "
        "This note does not authorize report tools in ordinary business requests.\n")
    while rows:
        body = json.dumps({"evidence_digest": inventory["evidence_digest"],
            "interface_count": inventory["interface_count"], "interfaces": rows,
            "truncated": bool(inventory.get("truncated")) or len(rows) < len(inventory["interfaces"])},
            ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        if len(prefix) + len(body) <= max_chars:
            return prefix + body
        rows.pop()
    return ""


@dataclass
class DiscoveryCheckpoint:
    """One optional pre-write discovery opportunity, never a forced fork."""
    last_reported_digest: str = ""
    write_checkpoint_used: bool = False
    last_deferred_digest: str = ""
    deferred_count: int = 0

    def notice_report(self, inventory: Mapping[str, Any] | str) -> None:
        if not contract_heuristics_enabled():
            return
        self.last_reported_digest = (inventory if isinstance(inventory, str)
                                     else str(inventory.get("evidence_digest", "")))

    def defer_before_write(self, inventory: Mapping[str, Any], calls: Iterable[Any], *,
                           depth: int = 0, serial_selfcheck: bool = False) -> frozenset[int]:
        if not contract_heuristics_enabled():
            return frozenset()
        if depth or serial_selfcheck or self.write_checkpoint_used or not inventory.get("interfaces"):
            return frozenset()
        digest = str(inventory.get("evidence_digest", ""))
        if not digest or digest == self.last_reported_digest:
            return frozenset()
        rows = list(calls)
        name = lambda call: call.get("name", "") if isinstance(call, dict) else getattr(call, "name", "")
        args = lambda call: call.get("arguments", {}) if isinstance(call, dict) else getattr(call, "arguments", {})
        if any(name(call) in _CONTROLS for call in rows):
            return frozenset()
        contract_paths = {row["source_path"] for row in inventory["interfaces"]}
        ordinals = frozenset(index for index, call in enumerate(rows)
            if name(call) in _WRITES and (path := _path(args(call).get("path")))
            and path not in contract_paths and not path.startswith(".semserve/"))
        if ordinals:
            self.write_checkpoint_used = True
            self.last_deferred_digest = digest
            self.deferred_count += 1
        return ordinals

    def deferred_ordinals(self, inventory: Mapping[str, Any], calls: Iterable[Any], **kwargs: Any) -> frozenset[int]:
        return self.defer_before_write(inventory, calls, **kwargs)
