"""Qwen3-32B proxy for the SemServe three-head frontier classifier.

The online input is cumulative Hybrid + Knowledge v4. Runtime-verified tool
facts are accumulated and deduplicated locally; executor-reported state deltas
are advisory and never replace real tool evidence.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import threading
import time
import urllib.request
from pathlib import Path
from typing import Any

from .classifier_state_memory import (
    RuntimeClassifierState,
    compact_tool_delta,
    is_validation_command,
)
from .parallel_control_v2 import DecisionContextV2, PredictionV2, VALUE_ONLY_MODEL_SUFFIX
from .dynamic_frontier import MAX_FRONTIER_CANDIDATES, canonical_work_unit_id, g1_enabled


INPUT_VERSION = "semserve.cumulative-hybrid-knowledge.v4"
VALUE_ONLY_OUTPUT_MODE = "value_v2"
VALUE_REASON_MAX_CHARS = 240
BRANCH_PROFILE_LEVELS = {
    "difficulty": ("low", "medium", "high"),
    "length": ("short", "medium", "long"),
}
VALUE_SYSTEM_PROMPT = """Decide whether issuing an Offer to delegate concurrent work is worthwhile now.
Use only the supplied task, Runtime-verified candidates, evidence, and execution state.
The Runtime validates dependencies and decides the width cap. Do not return a plan or width.
Use the embedded decision knowledge for evidence and tradeoffs. Follow this output contract
when it differs from the legacy decision knowledge.
Conflict-free branches are eligible for parallelism. Estimate its value from the work that can
overlap and the expected coordination cost. Use branch_profiles as qualitative estimates of
remaining difficulty and length. Favor an Offer for substantial independent work of similar
length when coordination appears modest. Short or easy branches can still be worthwhile when
their overlap or independent verification justifies the overhead. Assess these tradeoffs from
the visible work even when exact runtimes are unknown.
Compare the candidate group, not just its hardest branch, using these qualitative load patterns:
- Balanced substantial work: at least two independent branches still need meaningful implementation
  and focused verification. Similar remaining lengths can provide useful overlap; favor an Offer
  when that work or a specific correctness benefit plausibly covers delegation overhead.
- One long branch with short companions: the longest branch can still dominate join time, and
  the overlap mainly hides the companions' remaining work. A difficult long branch alone does not
  justify delegating the group. Check whether the companions contribute enough useful overlap or
  specific independent verification to cover planning, Fork context, repeated checks and join.
- All light work: check whether the parent can finish by reusing existing logic with a few ordinary
  tool calls. Creating children needs a concrete overlap or independent-verification benefit beyond
  that serial alternative. Do not assume independent wrappers need independent implementations.
These are comparison patterns, not hard acceptance or rejection rules based on difficulty/length.
Prioritize expected strict task correctness. When correctness is comparable, consider whether useful
overlap on the critical path will outweigh planning, child context, repeated work, checks and join.
Different paths or inputs may share an implementation. Consider implementing shared logic once.
Do not invent unseen evidence, speed estimates or verifier outcomes. If the evidence does not support
a benefit, choose false. Return only JSON with a boolean worth_parallel and a short reason grounded in
specific visible work or evidence. When profiles are provided, cite a relevant estimate and the
coordination tradeoff. Preserve differences between candidates when citing mixed profiles.
Identify the load pattern, the concrete work that can overlap or benefit from independent
verification, and the main extra cost. No conflicts or an unsupported claim of modest coordination
alone is not sufficient justification for an Offer.
Use 1–2 sentences, no newlines, and at most 240 characters."""

VALUE_SCHEMA = {
    "type": "object",
    "properties": {
        "worth_parallel": {"type": "boolean"},
        "reason": {"type": "string", "minLength": 1, "maxLength": VALUE_REASON_MAX_CHARS},
    },
    "required": ["worth_parallel", "reason"],
    "additionalProperties": False,
}

SYSTEM_PROMPT = """You simulate the three classification heads of a small SemServe MLP.
Decide whether the NEXT executor-model turn should receive optional parallel-planning advice.
The task has no predeclared DAG. Infer readiness only from the supplied current evidence.
Runtime has verified, accumulated, bounded, and deduplicated durable tool facts in
cumulative_verified_state. cumulative_real_tool_evidence exposes the same durable facts in
tool-result form so you can inspect observed interfaces and inputs. llm_reported_state is
advisory and cannot by itself prove completion. programmatic_compact_state contains only
Runtime control facts about branches, joins, failures, budgets, and the current event.
current_frontier contains executor-proposed semantic work units that Runtime accepted only after
checking their evidence ids, observed read sets, workspace-local write ownership, completion
contracts, and pairwise conflicts. It is not a predeclared DAG or an expected label. Runtime does
not use a fixed surface taxonomy. ready_candidates are the only Runtime-verified immediate work
units; advisory_candidates are rejected or incomplete proposals and cannot increase safe width.
Judge whether the verified candidates are substantial enough to justify child-agent planning.

Return exactly one JSON object and no other text:
{"action":"parallel_ready","width":"3-4","workload":"medium"}

Allowed labels:
- action: serial | wait_for_input | parallel_ready
- width: 2 | 3-4 | 5-8 | 9-20
- workload: easy | medium | hard

Use parallel_ready only when at least two useful unfinished items have all concrete inputs now,
do not consume each other's future artifacts, and do not conflict on writes. Use wait_for_input
when multiple future items are visible but a contract, read result, generated artifact, join, or
other prerequisite is missing. Use serial for one useful next item, strict chains, shared
mutation, validation/integration, or completion. A list of requested files alone is not proof
that their interfaces and inputs are ready. parallel_ready means that creating two or more
sub-agents for substantial implementation/reasoning deliverables is useful now; it does not mean
that two read-only shell commands could be issued concurrently. If the task names an external
README, manifest, specification, schema, or other source of truth and Runtime has not verified
that contract was observed, do not return parallel_ready. Width counts ready branch deliverables,
not files, read calls, tests, or later consumers, and it must not exceed runtime_max_width.
For repair or completion of an existing target workspace, reading only the legacy
source/specification is insufficient: each proposed work unit must cite the concrete target and
source artifacts it inspected. For a greenfield target, nonexistent target-code inspection is not
required; the proposal must instead cite the observed contract/source inputs needed for each
owned output. Before parallel_ready, identify two Runtime-verified current deliverables, their
disjoint owned outputs, and one focused completion check per work unit. If you cannot, choose
serial or wait_for_input.
When current_frontier is present, never return a parallel width larger than safe_width. A
Runtime-derived investigation candidate can be substantial when it covers a coherent source
surface and must produce a bounded evidence artifact; do not reduce it to an individual read.

Generic calibration examples:
- Contract observed, but only legacy sources or one target implementation surface inspected:
  serial for existing-target repair; for a genuinely empty greenfield target, continue until the
  source-of-truth inputs needed by two disjoint output surfaces are complete.
- Contract observed and both target frontend and backend surfaces inspected, with independent
  changes, disjoint files, and focused checks ready: parallel_ready, width=2. Multiple files
  inside those two surfaces do not make width=3-4.
- One implementation remains, or successful build/verifier commands are integrating completed
  changes without two newly ready owned producers: serial.
The latest tool delta is not an exclusive next-action list. Re-evaluate the cumulative state:
an earlier inspected producer remains ready until evidence says it started, completed, failed,
became blocked, or was consumed by an integration step. Do not forget a ready frontend/module
producer merely because the latest read happened to focus on backend/another module.
Do not invent completed work, files, edges, or confidence. Output only the three labels."""


DECISION_KNOWLEDGE = {
    "version": "qwen32b-frontier-readiness-knowledge-v4.1-parallel-value",
    "purpose": (
        "General immediate-frontier readiness and qualitative parallel-value invariants; "
        "these contain no task identities, task labels, or predeclared DAG."
    ),
    "rules": [
        "A directory listing or unread files are inspection evidence, not independent deliverables.",
        "A unit is ready only after its contract and every concrete input are observed.",
        "When the task points to an external README, manifest, specification, schema, or source of truth, an unseen verified contract state forbids parallel_ready.",
        "Count only not-started useful deliverables; exclude running, completed, failed, and joined work.",
        "Two candidates are parallel only when neither consumes the other's future artifact and their writes do not conflict.",
        "A child-agent branch must be a substantial implementation, investigation, or reasoning deliverable; independent file reads, greps, or focused checks alone are tool concurrency, not branch width.",
        "Before parallel_ready, name at least two current producers and verify distinct owned artifacts or read-only outputs plus explicit completion checks.",
        "For repair of an existing target, legacy evidence alone is not readiness; each proposed work unit must cite its concrete observed target and source paths.",
        "For a greenfield port into an empty target, do not require nonexistent target files; use the fully observed external contract and source inputs to establish disjoint output ownership.",
        "Width follows Runtime-verified semantic work units, not a fixed vocabulary of frontend, backend, data, rules, or tests.",
        "Judge the immediate executable frontier, not whether the whole task is globally independent.",
        "A later fan-in consumer does not serialize two or more currently ready disjoint producers.",
        "After ready producers join, a single aggregator, validator, index, report, or integration step is serial.",
        "Shared directories are not conflicts when candidates own distinct named artifacts.",
        "Latest verified tool and Runtime state override older advisory LLM summary claims.",
        "Latest delta does not erase an earlier ready producer; retain it until verified started, completed, failed, blocked, or consumed.",
        "When two verified disjoint work units remain unfinished, focusing the newest read on one does not make the other serially dependent.",
        "Width counts independent unfinished frontier items, not files, reads, active branches, or downstream consumers.",
        "Action retains all readiness and safety requirements and also judges whether child-agent planning is worthwhile now; Workload rates remaining branch effort, not original task size.",
        "Use wait_for_input for visible future work with a missing or running prerequisite.",
        "After an offer is declined, do not repeat parallel_ready until new verified evidence changes candidate readiness, ownership, or required inputs.",
        "If all remaining work mutates one integration surface, choose serial even when several defects or checks are listed.",
        "A successful build or verifier followed by integration/final checks is serial unless new verified failures expose at least two owned producers.",
        "Assess the remaining verified frontier, not overall task size or file count; a complex task can still have only one useful next item.",
        "Favor independent multi-step reasoning, substantial implementation/debugging, or long required tool execution when useful overlap plausibly outweighs coordination.",
        "Independent reads, template edits, or a few short commands usually do not justify child agents; prefer ordinary tools when they complete the same work.",
        "Weigh useful overlap against planning, child context/startup, duplicated discovery/checks, and join/integration; do not invent timings or resource limits.",
        "Without exact timings, infer effort qualitatively from observed algorithms, code, inputs and focused checks; missing timing alone does not require serial.",
        "A serial tail limits whole-task speedup but does not cancel worthwhile overlap among currently ready producers.",
        "Choose width by substantial ready workstreams within safe_width and runtime_max_width; do not maximize width solely because more candidates exist.",
        "Return serial when verified ready work is trivial or coordination clearly dominates; use wait_for_input only for genuinely missing prerequisites, not unknown savings.",
    ],
    "decision_order": [
        "terminal_or_validation",
        "external_contract_observed_gate",
        "missing_contract_or_input",
        "running_or_join_blocked",
        "identify_immediate_ready_frontier",
        "exclude_tool_concurrency_and_tiny_items",
        "separate_ready_producers_from_downstream_consumers",
        "verify_owned_outputs_and_completion_checks",
        "check_concrete_artifact_or_write_dependency",
        "count_independent_not_started_frontier_items",
        "assess_remaining_branch_effort",
        "weigh_overlap_against_coordination_cost",
        "choose_useful_width_within_verified_frontier",
        "choose_action_width_workload",
    ],
}


def current_system_prompt() -> str:
    if not g1_enabled():
        return SYSTEM_PROMPT
    value = SYSTEM_PROMPT.replace(
        "Use parallel_ready only when at least two useful unfinished items have all concrete inputs now,\n"
        "do not consume each other's future artifacts, and do not conflict on writes.",
        "Use parallel_ready only when at least two useful unfinished CURRENT OPERATIONS have all coding "
        "inputs now and do not conflict on current reads or writes. A coding operation with "
        "validation_mode=isolated_fixture may defer the explicitly listed real validation inputs.",
    ).replace(
        "when multiple future items are visible but a contract, read result, generated artifact, join, or\n"
        "other prerequisite is missing. Use serial for one useful next item, strict chains, shared\n"
        "mutation, validation/integration, or completion.",
        "when an input required by the current operation is missing. A future generated artifact only "
        "blocks its real-input validation, not implementation from a complete observed interface. "
        "Use serial for one useful next operation, actual shared mutation, actual integration, or completion.",
    )
    return value + (
        "\nG1 operation boundary: Runtime derives coding_ready, validation_ready, current_operation, "
        "missing_validation_inputs and validation_inferred_needs. These are not model-declared test passes. "
        "Count only safe_candidate_ids for useful width. implement_and_check_private_fixture means the "
        "child must check a private fixture and deliver code; it must not fabricate or delete shared "
        "upstream outputs. Real validation can remain pending for the parent after join. Independent "
        "coding is allowed only when the actual coding read/write sets and public interfaces support it. "
        "Missing coding evidence, unsafe writes and actual integration dependencies remain hard gates."
    )


def current_decision_knowledge() -> dict[str, Any]:
    value = copy.deepcopy(DECISION_KNOWLEDGE)
    if not g1_enabled():
        return value
    replacements = {
        "A unit is ready only after its contract and every concrete input are observed.":
            "A current coding operation is ready only after its public contract and coding read_set "
            "are observed. Its explicit validation_read_set may be pending only in isolated_fixture mode.",
        "Two candidates are parallel only when neither consumes the other's future artifact and their writes do not conflict.":
            "Two current operations may overlap only when coding reads and writes do not conflict. "
            "Explicitly deferred real-input checks do not license reading missing future artifacts now.",
        "After ready producers join, a single aggregator, validator, index, report, or integration step is serial.":
            "Actual aggregation and real-input integration may remain serial. The corresponding code "
            "can be implemented earlier when its interface is complete and its current operation is independent.",
        "Width counts independent unfinished frontier items, not files, reads, active branches, or downstream consumers.":
            "Width counts independent unfinished current operations, not files, reads or active branches. "
            "Consumer implementation can count only when Runtime admitted its isolated_fixture operation.",
    }
    value["rules"] = [replacements.get(rule, rule) for rule in value["rules"]]
    value["g1_phase_aware"] = True
    return value


def _task_requires_external_contract(task: Any) -> bool:
    """Detect tasks whose executable contract lives in referenced external artifacts.

    This is a generic safety gate, not a benchmark-specific task or DAG label.
    """

    text = " ".join(str(task or "").lower().split())
    return any(token in text for token in (
        "readme", "manifest", "source of truth", "specification", "documented in",
        "schema file", "contract file", "requirements file",
    ))


def apply_runtime_prediction_constraints(
    heads: dict[str, str], model_input: dict[str, Any]
) -> tuple[dict[str, str], list[str]]:
    """Apply cheap Runtime-owned safety constraints after semantic prediction.

    The model still supplies the three heads.  These guards only reject states
    that contradict verified control facts; they never invent a positive DAG.
    """

    admitted = dict(heads)
    reasons: list[str] = []
    compact = model_input.get("programmatic_compact_state") or {}
    control = compact.get("execution_control") or {}
    verified = model_input.get("cumulative_verified_state") or {}
    frontier = model_input.get("current_frontier") or {}
    contract = verified.get("verified_contract_state") or {}
    reported = verified.get("llm_reported_state") or {}
    latest = model_input.get("latest_real_tool_delta") or []

    if admitted.get("action") == "parallel_ready":
        if (_task_requires_external_contract(model_input.get("original_task"))
                and contract.get("status", "unseen") == "unseen"):
            admitted["action"] = "serial"
            reasons.append("external_contract_unobserved")
        elif control.get("has_missing_input"):
            admitted["action"] = "wait_for_input"
            reasons.append("runtime_missing_input")
        elif int(control.get("join_pending") or 0) > 0:
            admitted["action"] = "wait_for_input"
            reasons.append("runtime_join_pending")
        elif control.get("has_write_conflict") or control.get("shared_write_conflicts"):
            admitted["action"] = "serial"
            reasons.append("runtime_write_conflict")
        if (admitted.get("action") == "parallel_ready"
                and not reported.get("ready_claims") and any(
            item.get("tool") == "shell"
            and item.get("ok")
            and is_validation_command(item.get("command"))
            for item in latest
        )):
            admitted["action"] = "serial"
            reasons.append("successful_validation_without_new_ready_branches")
        if (admitted.get("action") == "parallel_ready"
                and frontier.get("schema_version") != "semserve.dynamic-frontier.v2"):
            admitted["action"] = "serial"
            reasons.append("runtime_frontier_missing_or_unverified")
        elif (admitted.get("action") == "parallel_ready"
                and int(frontier.get("safe_width") or 0) < 2):
            admitted["action"] = (
                "wait_for_input" if frontier.get("ready_candidates") else "serial"
            )
            reasons.append("runtime_frontier_width_below_two")

    if admitted.get("action") != "parallel_ready":
        # Width is masked downstream. Keep schema-valid raw label in the audit
        # while preventing it from being interpreted as admitted branch width.
        return admitted, reasons

    maximum_width = int(compact.get("runtime_max_width") or 1)
    if frontier:
        maximum_width = min(maximum_width, int(frontier.get("safe_width") or 0))
    lower_bound = {"2": 2, "3-4": 3, "5-8": 5, "9-20": 9}[admitted["width"]]
    if lower_bound > maximum_width:
        if maximum_width < 2:
            admitted["action"] = "serial"
            reasons.append("runtime_width_below_two")
        elif maximum_width == 2:
            admitted["width"] = "2"
            reasons.append("width_clamped_to_runtime_max")
        elif maximum_width <= 4:
            admitted["width"] = "3-4"
            reasons.append("width_clamped_to_runtime_max")
        elif maximum_width <= 8:
            admitted["width"] = "5-8"
            reasons.append("width_clamped_to_runtime_max")
    return admitted, reasons


HEAD_SCHEMA = {
    "type": "object",
    "properties": {
        "action": {"type": "string", "enum": ["serial", "wait_for_input", "parallel_ready"]},
        "width": {"type": "string", "enum": ["2", "3-4", "5-8", "9-20"]},
        "workload": {"type": "string", "enum": ["easy", "medium", "hard"]},
    },
    "required": ["action", "width", "workload"],
    "additionalProperties": False,
}

ALLOWED = {
    "action": {"serial", "wait_for_input", "parallel_ready"},
    "width": {"2", "3-4", "5-8", "9-20"},
    "workload": {"easy", "medium", "hard"},
}

_DELTA_LOCK = threading.RLock()
_LIVE_DELTAS: dict[tuple[str, str], list[dict[str, Any]]] = {}


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _texts(raw: Any, *, limit: int = MAX_FRONTIER_CANDIDATES) -> list[str]:
    if not isinstance(raw, list):
        return []
    values: list[str] = []
    for item in raw[:limit]:
        text = " ".join(str(item).split())[:160]
        if text and text not in values:
            values.append(text)
    return values


def branch_profiles_enabled() -> bool:
    return os.environ.get("SEMSERVE_FRONTIER_BRANCH_PROFILES", "1") == "1"


def _branch_profile(report: dict[str, Any]) -> dict[str, str]:
    profile: dict[str, str] = {}
    for key, levels in BRANCH_PROFILE_LEVELS.items():
        value = report.get(key)
        if not isinstance(value, str) or value not in levels:
            return {}
        profile[key] = value
    return profile


def normalize_execution_delta(value: Any) -> dict[str, Any] | None:
    """Validate and bound one executor-authored state increment."""

    if not isinstance(value, dict):
        return None
    raw_ready = value.get("ready_upsert", value.get("ready", []))
    ready: list[dict[str, Any]] = []
    if isinstance(raw_ready, list):
        for raw in raw_ready[:MAX_FRONTIER_CANDIDATES]:
            if not isinstance(raw, dict):
                continue
            goal = " ".join(str(raw.get("goal", "")).split())[:160]
            if goal:
                contract = raw.get("completion_contract")
                contract = contract if isinstance(contract, dict) else {}
                ready.append(
                    {
                        "proposal_schema_version": "semserve.work-unit-proposal.v2",
                        "work_unit_id": " ".join(
                            str(raw.get("work_unit_id", "")).split()
                        )[:80],
                        "kind": " ".join(str(raw.get("kind", "work")).split())[:48],
                        "surface": " ".join(
                            str(raw.get("surface", "unit")).split()
                        )[:48],
                        "goal": goal,
                        "needs": _texts(raw.get("needs"), limit=6),
                        "read_set": _texts(raw.get("read_set", raw.get("reads")), limit=12),
                        "write_set": _texts(raw.get("write_set", raw.get("writes")), limit=12),
                        "evidence_ids": _texts(raw.get("evidence_ids"), limit=12),
                        "focused_check": " ".join(
                            str(raw.get("focused_check", "")).split()
                        )[:640],
                        "completion_contract": {
                            "required_artifact_paths": _texts(
                                contract.get("required_artifact_paths"), limit=12
                            ),
                            "required_test_targets": _texts(
                                contract.get("required_test_targets"), limit=4
                            ),
                        },
                        "workload_hint": " ".join(
                            str(raw.get("workload_hint", "medium")).split()
                        )[:16].lower(),
                        **_branch_profile(raw),
                    }
                )
                if g1_enabled():
                    validation_reads = raw.get("validation_read_set", [])
                    valid_validation_reads = (
                        isinstance(validation_reads, list) and len(validation_reads) <= 12
                        and all(isinstance(path, str) for path in validation_reads)
                    )
                    ready[-1].update(
                        # Keep an invalid declaration invalid for Runtime;
                        # silently coercing it to [] would erase a dependency.
                        validation_read_set=(_texts(validation_reads, limit=12)
                                             if valid_validation_reads else None),
                        validation_mode=str(raw.get("validation_mode") or "materialized_inputs").strip()[:48],
                    )
    phase = str(value.get("phase", "inspect")).strip().lower()
    if phase == "complete":
        phase = "done"
    if phase not in {"inspect", "implement", "validate", "integrate", "blocked", "done"}:
        phase = "inspect"
    return {
        "schema_version": "semserve.turn-state-delta.v1",
        "phase": phase,
        "done_add": _texts(value.get("done_add", value.get("done"))),
        "ready_upsert": ready,
        "ready_remove": _texts(value.get("ready_remove")),
        "blocked_add": _texts(value.get("blocked_add", value.get("blocked"))),
        "active_add": _texts(value.get("active_add", value.get("active"))),
        "active_remove": _texts(value.get("active_remove")),
    }


def store_execution_delta(
    run_id: str,
    scope_id: str,
    delta: dict[str, Any],
    reported_at_step: int,
) -> None:
    body = canonical([run_id, scope_id, reported_at_step, delta])
    envelope = {
        "delta_id": hashlib.sha256(body.encode("utf-8")).hexdigest(),
        "reported_at_step": reported_at_step,
        "delta": copy.deepcopy(delta),
    }
    with _DELTA_LOCK:
        key = (run_id, scope_id)
        rows = _LIVE_DELTAS.setdefault(key, [])
        if not any(row.get("delta_id") == envelope["delta_id"] for row in rows):
            rows.append(envelope)
        _LIVE_DELTAS[key] = rows[-16:]


def capture_execution_delta(
    run_id: str,
    scope_id: str,
    content: str,
    reported_at_step: int,
) -> tuple[dict[str, Any] | None, str | None]:
    """Capture one metadata line without treating it as a tool call."""

    matches = list(re.finditer(r"EXECUTION_DELTA_JSON:\s*", content or ""))
    if not matches:
        return None, "missing_metadata"
    try:
        raw, _ = json.JSONDecoder().raw_decode((content or "")[matches[-1].end() :])
    except (TypeError, ValueError):
        return None, "invalid_json"
    normalized = normalize_execution_delta(raw)
    if normalized is None:
        return None, "invalid_shape"
    store_execution_delta(run_id, scope_id, normalized, reported_at_step)
    return normalized, None


def compact_input(context: DecisionContextV2) -> dict[str, Any]:
    """Return the programmatic control part used by Hybrid v2."""

    memory = context.frontier_memory or {}
    active_subtasks = sum(
        1
        for node in context.dag_nodes
        if node.get("kind") == "subtask" and node.get("status") in {"pending", "ready", "running"}
    )
    completed_subtasks = sum(
        1
        for node in context.dag_nodes
        if node.get("kind") == "subtask" and node.get("status") in {"done", "succeeded"}
    )
    failed_subtasks = sum(
        1
        for node in context.dag_nodes
        if node.get("kind") == "subtask" and node.get("status") in {"failed", "cancelled"}
    )
    return {
        "step": context.step,
        "event": context.event,
        "plan_expansions": context.expansions,
        "remaining_expansions": context.remaining_expansions,
        "runtime_max_width": context.maximum_width,
        "pending_offer": context.pending_offer,
        "execution_control": {
            "last_event": memory.get("last_event", context.event),
            "active_subtask_count": active_subtasks,
            "completed_subtask_count": completed_subtasks,
            "failed_subtask_count": failed_subtasks,
            "join_pending": memory.get("join_pending", 0),
            "has_failed_predecessor": memory.get("has_failed_predecessor", False),
            "has_missing_input": memory.get("has_missing_input", False),
            "has_write_conflict": memory.get("has_write_conflict", False),
            "shared_write_conflicts": memory.get("shared_write_conflicts", []),
        },
    }


def parse_three_heads(content: str) -> dict[str, str]:
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", content.strip(), flags=re.IGNORECASE)
    candidates = [cleaned]
    match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
    if match and match.group(0) != cleaned:
        candidates.append(match.group(0))
    for candidate in candidates:
        try:
            value = json.loads(candidate)
        except (TypeError, ValueError):
            continue
        if not isinstance(value, dict):
            continue
        normalized = {key: str(value.get(key, "")).strip().lower() for key in ALLOWED}
        if all(normalized[key] in ALLOWED[key] for key in ALLOWED):
            return normalized
    raise ValueError("Qwen32B returned no valid three-head JSON object")


def parse_parallel_value(content: str) -> dict[str, Any]:
    value = json.loads(content)
    if not isinstance(value, dict) or set(value) != {"worth_parallel", "reason"}:
        raise ValueError("parallel value response requires worth_parallel and reason")
    if type(value["worth_parallel"]) is not bool:
        raise ValueError("worth_parallel must be a JSON boolean")
    reason = value["reason"]
    if (not isinstance(reason, str) or not reason.strip()
            or len(reason) > VALUE_REASON_MAX_CHARS or len(reason.splitlines()) != 1
            or "\n" in reason or "\r" in reason):
        raise ValueError("reason must be a short, nonempty, single-line string")
    return {"worth_parallel": value["worth_parallel"], "reason": reason.strip()}


def _without_profile_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {key: value for key, value in row.items() if key not in BRANCH_PROFILE_LEVELS}
        if isinstance(row, dict) else row
        for row in rows
    ]


def _without_profile_delta(delta: dict[str, Any]) -> dict[str, Any]:
    return {
        key: _without_profile_rows(value) if key in {"ready_upsert", "ready"} and isinstance(value, list) else value
        for key, value in delta.items()
    }


def _compact_predictor_tool_delta(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    clean_rows = []
    for row in rows:
        if row.get("tool") == "report_frontier_state":
            row = dict(row)
            if isinstance(row.get("arguments"), dict):
                row["arguments"] = _without_profile_delta(row["arguments"])
            result = row.get("result")
            if isinstance(result, dict) and isinstance(result.get("delta"), dict):
                row["result"] = {**result, "delta": _without_profile_delta(result["delta"])}
        clean_rows.append(row)
    return compact_tool_delta(clean_rows)


def project_branch_profiles(model_input: dict[str, Any], *, include: bool) -> None:
    """Keep candidate estimates in a single opt-in section of the wire input."""
    cumulative = model_input.get("cumulative_verified_state") or {}
    reported = cumulative.get("llm_reported_state") or {}
    claims = reported.get("ready_claims") or []
    if include:
        frontier = model_input.get("current_frontier") or {}
        safe_ids = set(frontier.get("safe_candidate_ids") or ())
        profiles = {}
        for claim in claims:
            candidate_id = canonical_work_unit_id(claim.get("work_unit_id"))
            profile = _branch_profile(claim)
            if candidate_id in safe_ids and profile:
                profiles[candidate_id] = profile
        if profiles:
            model_input["branch_profiles"] = profiles

    if "ready_claims" in reported:
        # These rows can share references with the Runtime claim store.
        reported["ready_claims"] = _without_profile_rows(claims)
    if isinstance(reported.get("latest_delta"), dict):
        reported["latest_delta"] = _without_profile_delta(reported["latest_delta"])


class Qwen32BFrontierPredictor:
    def __init__(
        self,
        *,
        endpoint: str = "http://127.0.0.1:39232/v1/chat/completions",
        model: str = "Qwen3-32B",
        audit_path: str | Path | None = None,
        timeout_seconds: float = 120.0,
        api_key: str = "",
        portable_openai_compatible: bool = False,
        output_mode: str | None = None,
        include_branch_profiles: bool | None = None,
    ) -> None:
        self.endpoint = endpoint
        self.model = model
        self.audit_path = Path(audit_path) if audit_path is not None else None
        self.timeout_seconds = timeout_seconds
        self.api_key = api_key
        self.portable_openai_compatible = portable_openai_compatible
        self.output_mode = (output_mode if output_mode is not None
                            else os.environ.get("SEMSERVE_QWEN_PREDICTOR_OUTPUT", VALUE_ONLY_OUTPUT_MODE))
        if self.output_mode not in {"three_heads", VALUE_ONLY_OUTPUT_MODE}:
            raise ValueError(f"Unknown Qwen predictor output mode: {self.output_mode}")
        self.include_branch_profiles = (
            branch_profiles_enabled() if include_branch_profiles is None else include_branch_profiles
        )
        self._lock = threading.RLock()
        self._runtime_states: dict[tuple[str, str], RuntimeClassifierState] = {}
        if self.audit_path is not None:
            self.audit_path.parent.mkdir(parents=True, exist_ok=True)

    def build_input(self, context: DecisionContextV2) -> dict[str, Any]:
        key = (context.run_id, context.scope_id)
        with self._lock:
            state = self._runtime_states.setdefault(key, RuntimeClassifierState())
            latest_rows = state.merge_observations(context.observations, context.step)
            with _DELTA_LOCK:
                deltas = copy.deepcopy(_LIVE_DELTAS.get(key, []))
            state.merge_llm_deltas(deltas, context.step)
            cumulative, cumulative_evidence = state.predictor_views(context.task)
        model_input = {
            "schema_version": INPUT_VERSION,
            "input_arm": "cumulative_hybrid_knowledge",
            "original_task": context.task,
            "current_frontier": copy.deepcopy(
                cumulative.get("dynamic_frontier") or {}
            ),
            "cumulative_verified_state": cumulative,
            "cumulative_real_tool_evidence": cumulative_evidence,
            "latest_real_tool_delta": _compact_predictor_tool_delta(latest_rows),
            "programmatic_compact_state": compact_input(context),
            "learned_error_knowledge": current_decision_knowledge(),
        }
        project_branch_profiles(
            model_input,
            include=self.output_mode == VALUE_ONLY_OUTPUT_MODE and self.include_branch_profiles,
        )
        return model_input

    def predict(self, context: DecisionContextV2) -> PredictionV2:
        model_input = self.build_input(context)
        input_json = canonical(model_input)
        value_only = self.output_mode == VALUE_ONLY_OUTPUT_MODE
        schema_name, schema = ("semserve_parallel_value_v2", VALUE_SCHEMA) if value_only else (
            "semserve_mlp_three_heads", HEAD_SCHEMA
        )
        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": VALUE_SYSTEM_PROMPT if value_only else current_system_prompt()},
                {"role": "user", "content": input_json},
            ],
            "temperature": 0,
            "top_p": 1,
            "max_tokens": 160 if value_only else 96,
            "stream": False,
            "chat_template_kwargs": {"enable_thinking": False},
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": schema_name, "strict": True, "schema": schema},
            },
        }
        if self.portable_openai_compatible:
            # Ofox forwards Qwen's native chat-template control, which is
            # required to suppress the reasoning preamble for this small
            # classification request.  Its Qwen route does not implement the
            # OpenAI json_schema response format reliably, so keep the prompt
            # contract and remove only that provider-specific constraint.
            body.pop("response_format", None)
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        request = urllib.request.Request(
            self.endpoint,
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        started = time.time()
        perf_started = time.perf_counter()
        raw_content = ""
        error = None
        response_data: dict[str, Any] = {}
        raw_heads: dict[str, str] = {}
        admitted_heads: dict[str, str] = {}
        constraint_reasons: list[str] = []
        raw_value: dict[str, Any] | None = None
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                response_data = json.loads(response.read().decode("utf-8"))
            raw_content = response_data["choices"][0]["message"].get("content") or ""
            if value_only:
                raw_value = parse_parallel_value(raw_content)
                # Internal compatibility with the existing safety checks.
                heads = {"action": "parallel_ready" if raw_value["worth_parallel"] else "serial",
                         "width": "2", "workload": "medium"}
            else:
                raw_heads = parse_three_heads(raw_content)
                heads = raw_heads
            admitted_heads, constraint_reasons = apply_runtime_prediction_constraints(
                heads, model_input
            )
        except BaseException as exc:
            error = {"type": type(exc).__name__, "message": str(exc)}
            raise
        finally:
            if self.audit_path is not None:
                components = {
                    key: len(canonical(value))
                    for key, value in model_input.items()
                    if key not in {"schema_version", "input_arm"}
                }
                row = {
                    "schema_version": "qwen32b-frontier-predictor-audit/v2",
                    "started": started,
                    "latency_seconds": round(time.perf_counter() - perf_started, 6),
                    "context": {
                        "run_id": context.run_id,
                        "scope_id": context.scope_id,
                        "step": context.step,
                        "event": context.event,
                    },
                    "input": model_input,
                    "input_chars": len(input_json),
                    "component_chars": components,
                    "input_sha256": hashlib.sha256(input_json.encode("utf-8")).hexdigest(),
                    "raw_content": raw_content,
                    "raw_heads": raw_heads,
                    "admitted_heads": admitted_heads,
                    "constraint_reasons": constraint_reasons,
                    "usage": response_data.get("usage"),
                    "error": error,
                }
                if value_only:
                    row.update(output_mode=self.output_mode, raw_value=raw_value)
                encoded = json.dumps(row, ensure_ascii=False, sort_keys=True)
                with self._lock:
                    with self.audit_path.open("a", encoding="utf-8", newline="\n") as handle:
                        handle.write(encoded + "\n")

        parallel = admitted_heads["action"] == "parallel_ready"
        if value_only:
            return PredictionV2(
                action=admitted_heads["action"],
                width=min(context.maximum_width, 20) if parallel else None,
                workload_level="medium",
                model_version=self.model + VALUE_ONLY_MODEL_SUFFIX,
                reason=raw_value["reason"],
                input_version=INPUT_VERSION,
                input_fingerprint=hashlib.sha256(input_json.encode("utf-8")).hexdigest(),
            )
        return PredictionV2(
            action=admitted_heads["action"],
            width=None,
            width_bucket=admitted_heads["width"] if parallel else None,
            workload_level=admitted_heads["workload"],
            confidence=1.0,
            model_version=f"{self.model}-cumulative-hybrid-knowledge-v4",
            reason=("Qwen3-32B proxy for the future MLP three heads"
                    + ("; runtime_guard=" + ",".join(constraint_reasons)
                       if constraint_reasons else "")),
            input_version=INPUT_VERSION,
            input_fingerprint=hashlib.sha256(input_json.encode("utf-8")).hexdigest(),
        )
