"""Runtime validation for LLM-proposed immediate work units.

The executor model may propose semantic work units from the evidence it has
just observed. Runtime never trusts those proposals directly: it validates
their evidence references, observed read set, workspace-local write ownership,
completion contract, and pairwise conflicts before exposing them to the
three-head predictor. No task-specific surface taxonomy or predeclared DAG is
used here.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import PurePosixPath
from typing import Any

from .frontier_contract import (
    FRONTIER_REPORT_MAX_BYTES,
    frontier_report_schema,
    is_frontier_report_path,
)
from .validation_progress import EXCEPTION, FRAME, MISSING_FILE


# Bound the immediate frontier, not a backlog of future-wave consumers.
# The current width8 profile still validates dependencies and write conflicts.
MAX_FRONTIER_CANDIDATES = 8
MAX_PATHS_PER_CANDIDATE = 12
MAX_EVIDENCE_IDS_PER_CANDIDATE = 12
MAX_CHECK_CHARS = 640
_WORKLOADS = {"easy", "medium", "hard"}


def g1_enabled() -> bool:
    """Keep the original frontier/three-head wire unchanged unless opted in."""
    return os.getenv("SEMSERVE_G1") == "1"


def _g1_validation_state(candidate, candidates, observed_paths, delivered, materialized):
    """Readiness is evidence-derived; availability never means a test passed.

    Validation inputs are separate from the files the current coding operation
    reads. An old materialized input cannot count as final when another live
    producer is about to replace it.
    """
    inputs = candidate["validation_read_set"]
    missing = [path for path in inputs if not (
        observed_paths.get(path.casefold(), {}).get("observation_level") in {"partial", "full"}
        or path in delivered or path in materialized
    )]
    producers = sorted({
        producer["id"] for producer in candidates if producer["id"] != candidate["id"]
        and any(_paths_overlap(written, consumed)
                for written in producer.get("write_set", []) for consumed in inputs)
    })
    candidate.update(
        validation_ready=not missing and not producers,
        missing_validation_inputs=missing,
        validation_inferred_needs=producers,
        local_check_passed=False,
        real_input_validation="pending" if inputs else "not_required_by_proposal",
        integration_pending=bool(inputs),
    )


def _path(value: Any) -> str:
    path = str(value or "").replace("\\", "/")
    while path.startswith("./"):
        path = path[2:]
    for root in ("/workspace", "/app"):
        if path.startswith(root + "/"):
            path = path[len(root) + 1:]
            break
        if path == root:
            return ""
    return path.lstrip("/")


def _slug(value: Any, *, fallback: str = "unit") -> str:
    text = re.sub(r"[^a-z0-9_.-]+", "-", str(value or "").strip().lower())
    return text.strip("-._")[:48] or fallback


def canonical_work_unit_id(value: Any) -> str:
    """One ID across raw proposals, validated frontiers and removals."""
    text = str(value or "").strip().lower()
    while text.startswith("llm:"):
        text = text[4:]
    slug = _slug(text, fallback="")
    return f"llm:{slug}" if slug else ""


def _safe_workspace_path(value: Any, *, allow_root: bool = False) -> str | None:
    raw = str(value or "").replace("\\", "/").strip()
    known_absolute = raw.startswith(("/workspace/", "/app/"))
    if (not raw or raw.startswith("~") or re.match(r"^[A-Za-z]:/", raw)
            or (raw.startswith("/") and not known_absolute)):
        return None
    path = _path(raw)
    parts = PurePosixPath(path.rstrip("/")).parts
    if not parts or any(part in {"", ".", ".."} for part in parts):
        return None
    if any(character in path for character in ("*", "?", "[", "]", "{", "}")):
        return None
    if not allow_root and path.rstrip("/").lower() in {
        "workspace", "generated_app", "src", "app", "tests", "test",
    }:
        return None
    return path


def _path_owned(root: str, path: str) -> bool:
    root_value = _path(root).rstrip("/")
    path_value = _path(path).rstrip("/")
    return bool(root_value and path_value) and (
        path_value == root_value or path_value.startswith(root_value + "/")
    )


def _paths_overlap(left: str, right: str) -> bool:
    return _path_owned(left, right) or _path_owned(right, left)


def _delivered_paths(tool_state: dict[str, Any]) -> set[str]:
    values: set[str] = set()
    for delivery in tool_state.get("branch_deliveries") or []:
        for raw_path in delivery.get("verified_artifact_paths") or []:
            if path := _path(raw_path):
                values.add(path)
        encoded = json.dumps(delivery, ensure_ascii=False)
        for match in re.finditer(
            r"(?:/workspace/)?\.semserve/frontier/[A-Za-z0-9_.-]+\.json", encoded
        ):
            if path := _path(match.group(0)):
                values.add(path)
    for write in tool_state.get("written_artifacts") or []:
        if write.get("delivery_verified") is True:
            if path := _path(write.get("path")):
                values.add(path)
    return values


def _materialized_writes(tool_state: dict[str, Any]) -> dict[str, int]:
    """Return successful parent/root writes visible at this boundary.

    A file does not need to be branch-delivered to prove that the parent has
    already materialized it. Such a write must not be offered as fresh child
    work unless a later verified failure explicitly justifies a repair.
    """

    values: dict[str, int] = {}
    for write in tool_state.get("written_artifacts") or []:
        path = _path(write.get("path"))
        if not path:
            continue
        values[path] = max(values.get(path, -1), int(write.get("last_step", -1)))
    return values


def _observed_artifacts(tool_state: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], set[str]]:
    paths: dict[str, dict[str, Any]] = {}
    evidence_ids: set[str] = set()
    for item in tool_state.get("discovered_input_artifacts") or []:
        path = _path(item.get("path"))
        if not path:
            continue
        evidence_id = str(item.get("evidence_id") or "")
        if evidence_id:
            evidence_ids.add(evidence_id)
        if g1_enabled() and item.get("source_evidence_id"):
            evidence_ids.add(str(item["source_evidence_id"]))
        paths[path.lower()] = {
            "path": path,
            "observation_level": str(item.get("observation_level") or "inventory"),
            "evidence_id": evidence_id,
        }
    return paths, evidence_ids


def _conflict(left: dict[str, Any], right: dict[str, Any]) -> str | None:
    for left_write in left.get("write_set") or []:
        for right_write in right.get("write_set") or []:
            if _paths_overlap(left_write, right_write):
                return "write_write"
        for right_read in right.get("read_set") or []:
            if _paths_overlap(left_write, right_read):
                return "write_read"
    for right_write in right.get("write_set") or []:
        for left_read in left.get("read_set") or []:
            if _paths_overlap(right_write, left_read):
                return "write_read"
    return None


def _is_completed(required_paths: list[str], delivered: set[str]) -> bool:
    return bool(required_paths) and all(
        any(_path_owned(required, actual) for actual in delivered)
        for required in required_paths
    )


def _materialized_step(
    required_paths: list[str], materialized: dict[str, int]
) -> int | None:
    matched_steps: list[int] = []
    for required in required_paths:
        matches = [
            step
            for actual, step in materialized.items()
            if _path_owned(required, actual)
        ]
        if not matches:
            return None
        matched_steps.append(max(matches))
    return max(matched_steps) if matched_steps else None


def _repair_is_justified(
    *,
    kind: str,
    goal: str,
    materialized_step: int,
    failures: list[dict[str, Any]],
    owned_paths: list[str],
) -> bool:
    repair_words = {"repair", "fix", "correct", "debug", "recover"}
    semantic_text = f"{kind} {goal}".lower()
    if materialized_step < 0 or not any(word in semantic_text for word in repair_words):
        return False
    for failure in failures:
        if int(failure.get("last_step", -1)) <= materialized_step:
            continue
        result = failure.get("result") or {}
        if result.get("not_executed") or result.get("ok") is True:
            continue
        diagnostic = str(result.get("output") or result.get("traceback") or result.get("error") or "")
        paths = [failure.get("path"), result.get("path")]
        missing = result.get("missing_artifact_paths")
        if isinstance(missing, list):
            paths.extend(missing)
        paths.extend(path for _, path in MISSING_FILE.findall(diagnostic))
        for traceback in re.split(r"(?m)^Traceback \(most recent call last\):[ \t]*$", diagnostic)[1:]:
            exceptions = EXCEPTION.findall(traceback)
            if not exceptions or exceptions[-1].startswith("subprocess.CalledProcessError:"):
                continue
            # A caller frame (including an already fixed renderer) does not
            # establish that its source caused the new failure.
            frames = [
                path for frame in FRAME.findall(traceback)
                if (path := _safe_workspace_path(frame, allow_root=True))
            ]
            paths.extend(frames[-1:])
        if any(
            _path_owned(owned, path)
            for raw_path in paths
            if (path := _safe_workspace_path(raw_path, allow_root=True))
            for owned in owned_paths
        ):
            return True
    return False


def _validate_proposal(
    raw: dict[str, Any],
    *,
    index: int,
    contract_observed: bool,
    observed_paths: dict[str, dict[str, Any]],
    observed_evidence_ids: set[str],
    delivered: set[str],
    materialized: dict[str, int],
    failures: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[str]]:
    errors: list[str] = []
    goal = " ".join(str(raw.get("goal") or "").split())[:240]
    kind = _slug(raw.get("kind"), fallback="work")
    surface = _slug(raw.get("surface"), fallback=f"unit-{index + 1}")
    candidate_id = canonical_work_unit_id(raw.get("work_unit_id"))
    if not candidate_id:
        fallback_id = hashlib.sha256(
            json.dumps([kind, surface, goal], ensure_ascii=False).encode("utf-8")
        ).hexdigest()[:12]
        candidate_id = canonical_work_unit_id(fallback_id)
    if not goal:
        errors.append("missing_goal")
    if not contract_observed:
        errors.append("external_contract_unobserved")

    read_set: list[str] = []
    for value in list(raw.get("read_set") or [])[:MAX_PATHS_PER_CANDIDATE]:
        path = _safe_workspace_path(value, allow_root=True)
        if path and path not in read_set:
            read_set.append(path)
        elif value:
            errors.append("unsafe_read_path")
    write_set: list[str] = []
    for value in list(raw.get("write_set") or [])[:MAX_PATHS_PER_CANDIDATE]:
        path = _safe_workspace_path(value)
        if path and path not in write_set:
            write_set.append(path)
        elif value:
            errors.append("unsafe_or_broad_write_path")
    if not read_set:
        errors.append("missing_read_set")
    if not write_set:
        errors.append("missing_write_set")

    missing_read_evidence_paths = [path for path in read_set if path.lower() not in observed_paths]
    if missing_read_evidence_paths:
        errors.append("unobserved_read_set")
    proposed_evidence_ids = [
        str(value)[:160]
        for value in list(raw.get("evidence_ids") or [])[:MAX_EVIDENCE_IDS_PER_CANDIDATE]
        if str(value or "").strip()
    ]
    if any(value not in observed_evidence_ids for value in proposed_evidence_ids):
        errors.append("unknown_evidence_id")
    evidence_ids = list(proposed_evidence_ids)
    for path in read_set:
        row = observed_paths.get(path.lower())
        if row and row.get("evidence_id") and row["evidence_id"] not in evidence_ids:
            evidence_ids.append(row["evidence_id"])
    if not evidence_ids:
        errors.append("missing_runtime_evidence")

    focused_check = " ".join(str(raw.get("focused_check") or "").split())[:MAX_CHECK_CHARS]
    if not focused_check:
        errors.append("missing_focused_check")
    contract = raw.get("completion_contract")
    contract = contract if isinstance(contract, dict) else {}
    required_paths: list[str] = []
    for value in list(contract.get("required_artifact_paths") or [])[:MAX_PATHS_PER_CANDIDATE]:
        path = _safe_workspace_path(value)
        if path and path not in required_paths:
            required_paths.append(path)
        elif value:
            errors.append("unsafe_required_artifact_path")
    if not required_paths:
        errors.append("missing_required_artifact_paths")
    elif any(not any(_path_owned(root, path) for root in write_set) for path in required_paths):
        errors.append("completion_contract_outside_write_set")
    test_targets = [
        " ".join(str(value).split())[:320]
        for value in list(contract.get("required_test_targets") or [])[:4]
        if str(value or "").strip()
    ]

    needs = [
        " ".join(str(value).split())[:160]
        for value in list(raw.get("needs") or [])[:6]
        if str(value or "").strip()
    ]
    workload = str(raw.get("workload_hint") or "medium").strip().lower()
    if workload not in _WORKLOADS:
        workload = "medium"
    if _is_completed(required_paths, delivered):
        errors.append("already_completed")
    else:
        last_materialized_step = _materialized_step(required_paths, materialized)
        if last_materialized_step is not None and not _repair_is_justified(
            kind=kind,
            goal=goal,
            materialized_step=last_materialized_step,
            failures=failures,
            owned_paths=write_set,
        ):
            errors.append("already_materialized_without_new_failure")

    candidate: dict[str, Any] = {
        "id": candidate_id,
        "kind": kind,
        "surface": surface,
        "goal": goal,
        "needs": needs,
        "needs_satisfied": not errors,
        "read_set": read_set,
        "write_set": write_set,
        "owned_outputs": write_set,
        "focused_check": focused_check or None,
        "completion_contract": {
            "required_artifact_kinds": ["file"],
            "required_artifact_paths": required_paths,
            "required_test_targets": test_targets,
        },
        "workload_hint": workload,
        "authority": "llm_dynamic_proposal_runtime_verified" if not errors else "llm_dynamic_proposal_rejected",
        "evidence_ids": evidence_ids,
        "proposal_schema_version": str(raw.get("proposal_schema_version") or ""),
    }
    if g1_enabled():
        validation_reads = []
        values = raw.get("validation_read_set", [])
        if not isinstance(values, list) or len(values) > MAX_PATHS_PER_CANDIDATE:
            errors.append("invalid_validation_read_set")
            values = []
        for value in values:
            path = _safe_workspace_path(value, allow_root=True)
            if path and path not in validation_reads:
                validation_reads.append(path)
            elif value:
                errors.append("unsafe_validation_read_path")
        mode = str(raw.get("validation_mode") or "materialized_inputs").strip()
        if mode not in {"isolated_fixture", "materialized_inputs"}:
            errors.append("invalid_validation_mode")
        candidate.update(validation_read_set=validation_reads, validation_mode=mode)
    report_paths = [path for path in required_paths if is_frontier_report_path(path)]
    if report_paths:
        if len(report_paths) != len(required_paths):
            errors.append("mixed_report_and_implementation_outputs")
        expected_report_path = f".semserve/frontier/{surface}-evidence.json"
        if len(surface) > 32 or report_paths != [expected_report_path]:
            errors.append("report_path_surface_mismatch")
        candidate.update({
            "max_output_bytes": FRONTIER_REPORT_MAX_BYTES,
            "report_schema": frontier_report_schema(surface),
            "delivery_tool": "deliver_frontier_report",
            "max_evidence_tool_calls": 32,
            "max_model_turns": 40,
        })
    else:
        missing_read_evidence_paths = [
            path for path in read_set
            if observed_paths.get(path.lower(), {}).get("observation_level") not in {"partial", "full"}
        ]
        if missing_read_evidence_paths:
            errors.append("implementation_read_set_not_inspected")
        candidate.update({"max_source_evidence_calls": 12, "max_model_turns": 0})
    if missing_read_evidence_paths:
        candidate["missing_read_evidence_paths"] = missing_read_evidence_paths
    candidate["needs_satisfied"] = not errors
    candidate["authority"] = (
        "llm_dynamic_proposal_runtime_verified"
        if not errors else "llm_dynamic_proposal_rejected"
    )
    return candidate, list(dict.fromkeys(errors))


def build_dynamic_frontier(
    task: str,
    contract_state: dict[str, Any],
    tool_state: dict[str, Any],
    llm_state: dict[str, Any],
    *,
    step: int,
) -> dict[str, Any]:
    """Validate a bounded immediate frontier proposed during execution."""

    del task  # No task-text regex or benchmark-specific surface vocabulary.
    contract_observed = contract_state.get("status", "unseen") != "unseen"
    observed_paths, observed_evidence_ids = _observed_artifacts(tool_state)
    delivered = _delivered_paths(tool_state)
    materialized = _materialized_writes(tool_state)
    failures = [
        item
        for item in (tool_state.get("recent_failures") or [])
        if isinstance(item, dict)
    ]
    candidates: list[dict[str, Any]] = []
    advisory: list[dict[str, Any]] = []
    rejection_counts: dict[str, int] = {}

    # The cumulative cache may retain completed producers until a later report
    # explicitly removes them.  Validate the entire bounded cache first; only
    # then cap the still-live frontier.  Capping raw claims at the front let an
    # older completed wave hide every candidate from the newest report.
    for index, raw in enumerate(llm_state.get("ready_claims") or []):
        if not isinstance(raw, dict):
            continue
        candidate, errors = _validate_proposal(
            raw,
            index=index,
            contract_observed=contract_observed,
            observed_paths=observed_paths,
            observed_evidence_ids=observed_evidence_ids,
            delivered=delivered,
            materialized=materialized,
            failures=failures,
        )
        if errors:
            for error in errors:
                rejection_counts[error] = rejection_counts.get(error, 0) + 1
            advisory.append({**candidate, "validation_errors": errors})
        else:
            candidates.append(candidate)

    candidates = candidates[-MAX_FRONTIER_CANDIDATES:]
    advisory = advisory[-MAX_FRONTIER_CANDIDATES:]

    # Infer immediate dependencies from proposed workspace paths. A concrete
    # artifact named in needs also counts when a candidate owns that path.
    blocked_candidates: list[dict[str, Any]] = []
    ready_candidates: list[dict[str, Any]] = []
    for candidate in candidates:
        declared_artifacts = {
            path.casefold() for value in candidate["needs"]
            if (path := _safe_workspace_path(value, allow_root=True))
        }
        if g1_enabled() and candidate["validation_mode"] == "isolated_fixture":
            # Only an explicitly separated validation dependency may be deferred.
            # Current coding reads and their write/read conflicts remain strict.
            declared_artifacts.difference_update(path.casefold() for path in candidate["validation_read_set"])
        inferred_needs = sorted({
            producer["id"]
            for producer in candidates
            if producer["id"] != candidate["id"]
            and not any(
                _paths_overlap(produced, candidate_write)
                for produced in producer.get("write_set") or []
                for candidate_write in candidate.get("write_set") or []
            )
            and (
                any(
                    _paths_overlap(produced, consumed)
                    for produced in producer["write_set"]
                    for consumed in candidate["read_set"]
                )
                or any(
                    produced.casefold() in declared_artifacts
                    for produced in producer["completion_contract"]["required_artifact_paths"]
                )
            )
        })
        candidate["inferred_needs"] = inferred_needs
        candidate["needs_satisfied"] = not inferred_needs
        if g1_enabled():
            candidate["coding_ready"] = not inferred_needs
            _g1_validation_state(candidate, candidates, observed_paths, delivered, materialized)
            must_wait = candidate["validation_mode"] == "materialized_inputs" and not candidate["validation_ready"]
            candidate["current_operation"] = (
                "wait_for_coding_inputs" if inferred_needs else
                "wait_for_validation_inputs" if must_wait else
                "implement_and_check_private_fixture" if candidate["validation_mode"] == "isolated_fixture" else
                "implement_and_check_materialized_inputs"
            )
            candidate["needs_satisfied"] = not inferred_needs and not must_wait
        else:
            must_wait = False
        if inferred_needs or must_wait:
            blocked_candidates.append(candidate)
        else:
            ready_candidates.append(candidate)

    conflict_matrix: dict[str, str] = {}
    for index, left in enumerate(ready_candidates):
        for right in ready_candidates[index + 1:]:
            reason = _conflict(left, right)
            conflict_matrix[f"{left['id']}|{right['id']}"] = reason or "none"

    safe_candidates: list[dict[str, Any]] = []
    for candidate in ready_candidates:
        if all(_conflict(candidate, selected) is None for selected in safe_candidates):
            safe_candidates.append(candidate)

    body = {
        "contract_status": contract_state.get("status", "unseen"),
        "ready_candidates": ready_candidates,
        "blocked_candidates": blocked_candidates,
        "advisory_candidates": advisory,
        "conflict_matrix": conflict_matrix,
        "rejection_counts": rejection_counts,
    }
    version = hashlib.sha256(
        json.dumps(body, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()
    return {
        "schema_version": "semserve.dynamic-frontier.v2",
        "frontier_version": version,
        "derived_at_step": step,
        "ready_candidates": ready_candidates,
        "blocked_candidates": blocked_candidates,
        "advisory_candidates": advisory,
        "conflict_matrix": conflict_matrix,
        "safe_candidate_ids": [item["id"] for item in safe_candidates],
        "safe_width": len(safe_candidates),
        "rejection_counts": dict(sorted(rejection_counts.items())),
        "observed_artifact_count": len(observed_paths),
        "verified_evidence_id_count": len(observed_evidence_ids),
        "source": "llm_dynamic_proposal_runtime_evidence_validated",
        "predeclared_dag": False,
    }
