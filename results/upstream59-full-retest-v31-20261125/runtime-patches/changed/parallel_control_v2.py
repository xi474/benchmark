"""Opt-in, event-driven semantic routing. No v1 prediction or resource API reuse.

The predictor contract is intentionally independent of the future neural model.
Resource score is a synthetic admission gate, NOT a measured benefit estimate.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import threading
import uuid
from dataclasses import asdict, dataclass, field, replace
from typing import Any, Literal, Protocol

from .planning import SPAWN_SUBTASKS_SCHEMA, InvalidTaskPlan, parse_task_plan

V2_TOOL = "choose_execution_mode_v2"
VERSION = "semserve.parallel-control.v2"
VALUE_ONLY_MODEL_SUFFIX = "-parallel-value-v2"
Action = Literal["serial", "wait_for_input", "parallel_ready"]


def _candidate_owns_path(candidate: dict[str, Any], path: str) -> bool:
    for raw_root in candidate.get("owned_outputs") or candidate.get("write_set") or []:
        root = str(raw_root).strip()
        if not root:
            continue
        if root.endswith("/") and path.startswith(root):
            return True
        if path == root:
            return True
    return False


def _bind_frontier_contracts(plan, offer: "OfferV2"):
    """Bind every accepted branch to exactly one Runtime-derived ready unit."""

    if not offer.frontier_candidates:
        return plan
    used: set[str] = set()
    bound = []
    for spec in plan.subtasks:
        matches = [
            candidate for candidate in offer.frontier_candidates
            if any(
                _candidate_owns_path(candidate, path)
                for path in spec.required_artifact_paths
            )
        ]
        if len(matches) != 1:
            raise InvalidTaskPlan(
                f"subtask {spec.id} must map by required_artifact_paths to exactly one "
                "runtime_verified_frontier_candidate"
            )
        candidate = matches[0]
        candidate_id = str(candidate.get("id") or "")
        if candidate_id in used:
            raise InvalidTaskPlan(
                f"runtime frontier candidate {candidate_id!r} was assigned to multiple branches"
            )
        used.add(candidate_id)
        candidate_contract = candidate.get("completion_contract") or {}
        required_paths = set(candidate_contract.get("required_artifact_paths") or [])
        if required_paths and not required_paths.issubset(set(spec.required_artifact_paths)):
            raise InvalidTaskPlan(
                f"subtask {spec.id} must preserve the runtime-verified completion contract "
                f"for frontier candidate {candidate_id!r}"
            )
        inputs = dict(spec.inputs)
        if candidate.get("report_schema"):
            inputs["_runtime_frontier_contract"] = {
                "candidate_id": candidate_id,
                "surface": candidate.get("surface"),
                "read_set": list(candidate.get("read_set") or []),
                "owned_outputs": list(candidate.get("owned_outputs") or []),
                "max_output_bytes": candidate.get("max_output_bytes"),
                "report_schema": copy.deepcopy(candidate.get("report_schema")),
                "delivery_tool": candidate.get("delivery_tool", "deliver_frontier_report"),
                "max_evidence_tool_calls": candidate.get("max_evidence_tool_calls", 32),
                "max_model_turns": candidate.get("max_model_turns", 40),
                "focused_check": candidate.get("focused_check"),
                "instructions": (
                    "Summarize decision-critical facts only. Do not dump source, enumerate "
                    "every field/control, or add keys outside report_schema."
                ),
            }
        else:
            inputs["_runtime_implementation_contract"] = {
                "candidate_id": candidate_id,
                "surface": candidate.get("surface"),
                "kind": candidate.get("kind"),
                "read_set": list(candidate.get("read_set") or []),
                "owned_outputs": list(candidate.get("owned_outputs") or []),
                "completion_contract": copy.deepcopy(candidate_contract),
                "focused_check": candidate.get("focused_check"),
                "max_source_evidence_calls": int(
                    candidate.get("max_source_evidence_calls") or 12
                ),
                # Zero means inherit the Runtime's task-wide max_steps. Complex
                # implementation branches must not be cut off by the much
                # smaller investigation-turn budget.
                "max_model_turns": int(candidate.get("max_model_turns") or 0),
                "instructions": (
                    "The Runtime-verified dynamic work-unit proposal and inherited parent facts "
                    "are the semantic handoff. Read only the listed read_set as needed, then "
                    "materialize the owned files and satisfy the exact completion contract. "
                    "Do not perform broad rediscovery or overlapping slice scans."
                ),
            }
            if os.environ.get("SEMSERVE_G1") == "1":
                inputs["_runtime_implementation_contract"].update({
                    key: copy.deepcopy(candidate.get(key)) for key in (
                        "validation_read_set", "validation_mode", "coding_ready",
                        "validation_ready", "missing_validation_inputs",
                        "validation_inferred_needs", "real_input_validation",
                        "current_operation", "integration_pending",
                    ) if key in candidate
                })
                inputs["_runtime_implementation_contract"]["instructions"] += (
                    " Inspect validation_read_set when available, or use private fixtures "
                    "for isolated_fixture local checks. Missing real upstream outputs must "
                    "not be fabricated in shared paths. Deliver owned code and local check "
                    "evidence now; the parent validates real inputs after join."
                )
        bound.append(replace(spec, inputs=inputs))
    return replace(plan, subtasks=tuple(bound))


def _requires_external_contract(task: str) -> bool:
    text = " ".join(str(task or "").lower().split())
    return any(token in text for token in (
        "readme", "manifest", "source of truth", "specification", "documented in",
        "schema file", "contract file", "requirements file",
    ))


def parallel_readiness_guard(context: "DecisionContextV2") -> str | None:
    """Reject positive predictions that contradict Runtime-verified control facts."""

    memory = context.frontier_memory or {}
    control = memory
    verified = memory.get("verified_classifier_state") or {}
    contract = verified.get("verified_contract_state") or {}
    frontier = verified.get("dynamic_frontier") or {}
    if frontier and int(frontier.get("safe_width") or 0) < 2:
        return "runtime_frontier_width_below_two"
    if (_requires_external_contract(context.task)
            and contract.get("status", "unseen") == "unseen"):
        return "external_contract_unobserved"
    if control.get("has_missing_input"):
        return "runtime_missing_input"
    if int(control.get("join_pending") or 0) > 0:
        return "runtime_join_pending"
    if control.get("has_write_conflict") or control.get("shared_write_conflicts"):
        return "runtime_write_conflict"
    return None


@dataclass(frozen=True)
class DecisionContextV2:
    run_id: str
    task_id: str
    scope_id: str
    node_id: str
    step: int
    event: str
    task: str
    observations: tuple[dict[str, Any], ...]
    dag_nodes: tuple[dict[str, Any], ...]
    tool_names: tuple[str, ...]
    expansions: int
    remaining_expansions: int
    maximum_width: int
    allowed_validator_refs: tuple[str, ...] = ()
    frontier_memory: dict[str, Any] = field(default_factory=dict)
    pending_offer: bool = False
    schema_version: str = VERSION
    # Trigger metadata only; not an additional trained predictor feature.
    fact_digest: str = ""

    def to_dict(self):
        return asdict(self)

    def fingerprint(self):
        # IDs, timestamps, repeated reads and model narration are not new facts.
        facts = sorted(set(json.dumps(
            {k: row[k] for k in ("tool", "arguments", "result")},
            sort_keys=True, ensure_ascii=False,
        ) for row in self.observations))
        # Re-evaluate when DAG status/event/admission bounds change, not just tool facts.
        body = [self.task, facts, self.expansions, self.tool_names, self.dag_nodes,
                self.frontier_memory, self.pending_offer,
                self.event, self.remaining_expansions, self.maximum_width, self.allowed_validator_refs,
                self.fact_digest]
        return hashlib.sha256(json.dumps(body, ensure_ascii=False).encode()).hexdigest()


@dataclass(frozen=True)
class PredictionV2:
    action: Action
    width: int | None = 1  # Legacy exact-width fixture only; new adapter sets None.
    workload_level: str = "easy"
    confidence: float = 1.0
    model_version: str = "mock-v2"
    evidence_ids: tuple[str, ...] = ()
    reason: str = ""
    width_bucket: str | None = None
    input_version: str = "legacy-v2"
    input_fingerprint: str = ""

    @property
    def value_only(self):
        return self.model_version.endswith(VALUE_ONLY_MODEL_SUFFIX)

    def validate(self, context):
        if self.action not in {"serial", "wait_for_input", "parallel_ready"}:
            raise ValueError("invalid v2 action")
        if self.width_bucket is not None:
            if self.width_bucket not in {"2","3-4","5-8","9-20"} or self.width is not None:
                raise ValueError("bucket cannot masquerade as exact width")
            if self.action != "parallel_ready": raise ValueError("nonparallel bucket must be masked")
        elif self.width is None:
            if self.action == "parallel_ready": raise ValueError("parallel prediction needs width bucket")
        elif type(self.width) is not int or not 1 <= self.width <= 20:
            raise ValueError("invalid legacy v2 width")
        elif self.action == "parallel_ready" and self.width < 2:
            raise ValueError("parallel_ready requires width >= 2")
        if self.workload_level not in {"easy", "medium", "hard"}:
            raise ValueError("invalid workload_level")
        if not math.isfinite(self.confidence) or not 0 <= self.confidence <= 1:
            raise ValueError("invalid confidence")
        observed = {row["evidence_id"] for row in context.observations}
        if not set(self.evidence_ids).issubset(observed):
            raise ValueError("prediction references unseen evidence")


class PredictorV2(Protocol):
    def predict(self, context: DecisionContextV2) -> PredictionV2: ...


@dataclass(frozen=True)
class ConfigV2:
    mode: str = "off"
    resource_score: float = 1.0
    resource_threshold: float = 0.5
    minimum_confidence: float = 0.8
    max_evaluations: int = 24
    max_offers: int = 4
    max_expansions: int = 4
    offer_ttl_steps: int = 2
    max_context_chars: int = 128000
    # Empty means each changed tool-result batch is potentially relevant.
    relevant_tools: tuple[str, ...] = ()
    width_admission_policy: str = "bucket_lower_bound"

    def __post_init__(self):
        if self.mode not in {"off", "shadow", "active"}:
            raise ValueError("invalid v2 mode")
        if self.width_admission_policy not in {"bucket_lower_bound", "bucket_upper_bound"}:
            raise ValueError("invalid v2 width admission policy")
        for value in (self.resource_score, self.resource_threshold, self.minimum_confidence):
            if not math.isfinite(value) or not 0 <= value <= 1:
                raise ValueError("v2 scores must be finite in [0,1]")
        for value in (self.max_evaluations, self.max_offers, self.max_expansions,
                      self.offer_ttl_steps, self.max_context_chars):
            if type(value) is not int or value < 1:
                raise ValueError("v2 budgets must be positive integers")


@dataclass(frozen=True)
class OfferV2:
    offer_id: str
    context_fingerprint: str
    created_step: int
    expires_after_step: int
    maximum_width: int
    prediction: PredictionV2
    allowed_validator_refs: tuple[str, ...]
    resource_score: float
    frontier_candidates: tuple[dict[str, Any], ...] = ()
    schema_version: str = VERSION


class MockPredictorV2:
    """Explicit test fixture. First matching observed-state rule wins.

    Rules inspect real tool results only; they cannot inject facts or tools.
    Never presented as a trained MLP or general semantic classifier.
    """
    def __init__(self, rules=(), default=None):
        self.rules = tuple(rules)
        self.default = default or {"action": "serial"}

    def predict(self, context):
        for rule in self.rules:
            if rule.get("event") not in (None, context.event):
                continue
            if rule.get("expansions") not in (None, context.expansions):
                continue
            matches = [o for o in context.observations
                       if o["tool"] == rule.get("tool")
                       and rule.get("contains", "") in json.dumps(o["result"], ensure_ascii=False)]
            if "tool" in rule and not matches:
                continue
            prediction = PredictionV2(**rule["prediction"])
            return replace(prediction, evidence_ids=tuple(o["evidence_id"] for o in matches))
        return PredictionV2(**self.default)


class ControllerV2:
    def __init__(self, config=None, predictor=None):
        self.config = config or ConfigV2()
        self.predictor = predictor
        if self.config.mode != "off" and predictor is None:
            raise ValueError("enabled v2 requires an explicit predictor")
        self._seen = set()
        self._counts = {}
        self._offers = {}
        self._offer_owners = {}
        self._lock = threading.RLock()

    @property
    def mode(self):
        return self.config.mode

    def evaluate(self, context, pending_offer=None):
        fingerprint = context.fingerprint()
        result = {"schema_version": VERSION, "fingerprint": fingerprint,
                  "mode": self.mode, "resource_source": "constant_placeholder",
                  "resource_score": self.config.resource_score, "reason": "disabled"}
        if self.mode == "off":
            return None, result
        key = (context.run_id, context.scope_id)
        with self._lock:
            seen_key = (*key, fingerprint)
            if seen_key in self._seen:
                return None, {**result, "reason": "unchanged_state"}
            counts = self._counts.setdefault(key, {"evaluations": 0, "offers": 0})
            if counts["evaluations"] >= self.config.max_evaluations:
                return None, {**result, "reason": "evaluation_budget_exhausted"}
            refreshing = (pending_offer is not None and
                          self._offers.get(pending_offer.offer_id) == "pending" and
                          self._offer_owners.get(pending_offer.offer_id) == key)
            # Shadow mode intentionally measures predictions without emitting offers.
            if self.mode == "active" and (context.remaining_expansions < 1 or
                    (counts["offers"] >= self.config.max_offers and not refreshing)):
                return None, {**result, "reason": "expansion_or_offer_budget_exhausted"}
            # Deduplicate consecutive states, not a state revisited after changes.
            self._seen = {item for item in self._seen if item[:2] != key}
            self._seen.add(seen_key)
            counts["evaluations"] += 1
            if len(json.dumps(context.to_dict(), ensure_ascii=False)) > self.config.max_context_chars:
                return None, {**result, "reason": "context_too_large"}
            try:
                prediction = self.predictor.predict(copy.deepcopy(context))
                prediction.validate(context)
            except Exception as exc:
                return None, {**result, "reason": "predictor_error", "error_type": type(exc).__name__}
            result["prediction"] = asdict(prediction)
            if prediction.confidence < self.config.minimum_confidence:
                return None, {**result, "reason": "low_confidence"}
            if prediction.action != "parallel_ready":
                return None, {**result, "reason": prediction.action}
            guard_reason = parallel_readiness_guard(context)
            if guard_reason is not None:
                return None, {**result, "reason": guard_reason, "runtime_guarded": True}
            if self.config.resource_score < self.config.resource_threshold:
                return None, {**result, "reason": "resource_placeholder_denied"}
            if context.remaining_expansions < 1 or (counts["offers"] >= self.config.max_offers and not refreshing):
                return None, {**result, "reason": "expansion_or_offer_budget_exhausted"}
            if prediction.value_only:
                requested_limit = prediction.width
            elif prediction.width_bucket is not None:
                # Explicit conservative admission policy; never claim this is exact semantic width.
                limits = ({"2":2,"3-4":4,"5-8":8,"9-20":20}
                          if self.config.width_admission_policy == "bucket_upper_bound"
                          else {"2":2,"3-4":3,"5-8":5,"9-20":9})
                requested_limit = limits[prediction.width_bucket]
            else:
                requested_limit = prediction.width
            verified = (context.frontier_memory or {}).get("verified_classifier_state") or {}
            frontier = verified.get("dynamic_frontier") or {}
            safe_width = int(frontier.get("safe_width") or context.maximum_width)
            width = min(context.maximum_width, requested_limit, safe_width)
            if prediction.value_only:
                width_policy = "runtime_verified_frontier_cap"
            else:
                width_policy = ("predictor_bucket_upper_capped_by_runtime_v1"
                                if self.config.width_admission_policy == "bucket_upper_bound"
                                else "predictor_lower_bound_capped_by_runtime_v3")
            result.update(width_bucket=prediction.width_bucket, width_policy=width_policy,
                          suggested_width=requested_limit, runtime_branch_limit=width, admitted_branch_limit=width)
            if width < 2:
                return None, {**result, "reason": "width_below_two"}
            if self.mode == "shadow":
                return None, {**result, "reason": "shadow_would_offer"}
            safe_ids = set(frontier.get("safe_candidate_ids") or [])
            candidates = tuple(
                copy.deepcopy(item)
                for item in frontier.get("ready_candidates", [])
                if item.get("id") in safe_ids
            )[:width]
            offer = OfferV2(
                offer_id=(
                    pending_offer.offer_id
                    if refreshing else "v2-" + uuid.uuid4().hex[:12]
                ),
                context_fingerprint=fingerprint,
                created_step=context.step,
                expires_after_step=context.step + self.config.offer_ttl_steps,
                maximum_width=width,
                prediction=prediction,
                allowed_validator_refs=context.allowed_validator_refs,
                resource_score=self.config.resource_score,
                frontier_candidates=candidates,
            )
            if not refreshing:
                counts["offers"] += 1
            self._offers[offer.offer_id] = "pending"
            self._offer_owners[offer.offer_id] = key
            return offer, {**result, "reason": "offer_refreshed" if refreshing else "offer_created", "offer": asdict(offer)}

    def close(self, offer):
        with self._lock:
            self._offers[offer.offer_id] = "closed"

    def finish(self, run_id, scope_id):
        """Release per-run state on success, failure or cancellation."""
        key = (run_id, scope_id)
        with self._lock:
            self._counts.pop(key, None)
            self._seen = {item for item in self._seen if item[:2] != key}
            for offer_id in [oid for oid, owner in self._offer_owners.items() if owner == key]:
                self._offer_owners.pop(offer_id, None)
                self._offers.pop(offer_id, None)

    def parse(self, arguments, offer, step, max_subtasks):
        with self._lock:
            if self._offers.get(offer.offer_id) != "pending":
                raise InvalidTaskPlan("v2 offer is not pending")
            if step > offer.expires_after_step:
                raise InvalidTaskPlan("v2 offer expired")
            if isinstance(arguments, dict) and "mode" in arguments:
                if (set(arguments) != {"offer_id", "mode", "reason", "plan"}
                        or arguments["mode"] != "parallel"
                        or not isinstance(arguments["reason"], str)
                        or not arguments["reason"].strip()):
                    raise InvalidTaskPlan("parallel choice requires offer_id, mode, nonempty reason and plan")
                arguments = {"offer_id": arguments["offer_id"], "plan": arguments["plan"]}
            # Read compatibility for existing v2 traces; new schema exposes mode/reason.
            if not isinstance(arguments, dict) or set(arguments) != {"offer_id", "plan"}:
                raise InvalidTaskPlan("v2 requires an explicit choice or legacy offer_id and plan")
            if arguments["offer_id"] != offer.offer_id:
                raise InvalidTaskPlan("stale v2 offer_id")
            plan = parse_task_plan(arguments["plan"], max_subtasks=min(max_subtasks, offer.maximum_width),
                                   strict_model_contract=True)
            plan = _bind_frontier_contracts(plan, offer)
            # Advisory experiment: do not semantically veto a structurally valid model DAG.
            if set(plan.acceptance_policy.validators) - set(offer.allowed_validator_refs):
                raise InvalidTaskPlan("unauthorized v2 validator")
            # Recheck synthetic admission at consumption; no real-resource claim.
            if self.config.resource_score < self.config.resource_threshold:
                raise InvalidTaskPlan("v2 resource placeholder denied")
            names = {s.id: f"{offer.offer_id}-{i}" for i, s in enumerate(plan.subtasks)}
            plan = replace(plan, subtasks=tuple(replace(s, id=names[s.id],
                           depends_on=tuple(names[d] for d in s.depends_on)) for s in plan.subtasks))
            self._offers[offer.offer_id] = "consumed"
            return plan, names

    def decline(self, arguments, offer, step):
        with self._lock:
            if self._offers.get(offer.offer_id) != "pending" or step > offer.expires_after_step:
                raise InvalidTaskPlan("v2 offer is closed or expired")
            if (not isinstance(arguments, dict)
                    or set(arguments) != {"offer_id", "mode", "reason"}
                    or arguments["offer_id"] != offer.offer_id
                    or arguments["mode"] not in {"serial", "decline"}
                    or not isinstance(arguments["reason"], str)
                    or not arguments["reason"].strip()):
                raise InvalidTaskPlan("serial/decline requires matching offer_id and nonempty reason; omit plan")
            self._offers[offer.offer_id] = "closed"

    @staticmethod
    def schema(offer):
        plan = copy.deepcopy(SPAWN_SUBTASKS_SCHEMA["function"]["parameters"])
        plan["properties"]["subtasks"].update(minItems=2, maxItems=offer.maximum_width)
        validators = plan["properties"]["acceptance_policy"]["properties"]["validators"]
        if offer.allowed_validator_refs:
            validators["items"]["enum"] = list(offer.allowed_validator_refs)
        else:
            validators["maxItems"] = 0
        return {"type": "function", "function": {
            "name": V2_TOOL,
            "description": (
                "Required response to the pending Runtime offer. Call exactly once before any "
                "ordinary tool call and copy the exact pending offer_id. Choose mode=parallel "
                "with a nonempty dependency-correct plan, "
                "or mode=serial/decline with a nonempty reason and no plan."
            ),
            "parameters": {"type": "object", "additionalProperties": False,
                "required": ["offer_id", "mode", "reason"], "properties": {
                    "offer_id": {"type": "string", "enum": [offer.offer_id]},
                    "mode": {"type": "string", "enum": ["parallel", "serial", "decline"]},
                    "reason": {"type": "string", "minLength": 1}, "plan": plan}}}}

    @staticmethod
    def prompt(offer):
        forced = os.environ.get("AGENT_RUNTIME_OFFER_RESPONSE_POLICY") == "forced_parallel"
        decision_rule = (
            "This is a mandatory parallelization offer. In your next model turn, call exactly "
            "one choose_execution_mode_v2 with mode=parallel, a nonempty reason, and your own "
            "plan. Do not call ordinary tools, answer the task, decline, or continue serially "
            "while this offer is pending. "
            if forced else
            "You must respond to this offer in your next model turn, but you are not required to "
            "accept it. Call exactly one choose_execution_mode_v2 and copy the exact offer_id "
            "shown above. Choose mode=parallel with a "
            "nonempty dependency-correct plan only when at least two useful branches are ready now; "
            "otherwise choose mode=serial or mode=decline with a nonempty reason and omit plan. "
            "Never return an empty subtask list. Do not call ordinary tools or answer the task "
            "until the offer has been resolved. "
        )
        candidate_payload = json.dumps(
            list(offer.frontier_candidates),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        width_advice = (
            "" if offer.prediction.value_only else
            f"suggested_width_bucket: {offer.prediction.width_bucket or offer.prediction.width} (advice only)\n"
        )
        workload_advice = "" if offer.prediction.value_only else f"workload_level: {offer.prediction.workload_level}\n"
        width_basis = ("verified frontier and Runtime" if offer.prediction.value_only
                       else "prediction advice capped by verified frontier and Runtime")
        return (f"[RUNTIME_PARALLEL_OFFER_V2]\noffer_id: {offer.offer_id}\n"
                f"{width_advice}"
                f"runtime_max_subtasks: {offer.maximum_width} ({width_basis})\n"
                f"runtime_verified_frontier_candidates: {candidate_payload}\n"
                "Choose the number of branches from actual independent work and do not exceed runtime_max_subtasks. "
                f"{workload_advice}"
                + decision_rule +
                "Do not combine multiple planning/decision calls; "
                "ordinary calls in the same turn must be independent of the plan's outputs. "
                "Use runtime_verified_frontier_candidates as the immediate evidence-backed work set. "
                "You may decline a candidate that is not substantial, but do not replace it with future-wave work. "
                "For investigation candidates, write the bounded evidence artifact at owned_outputs and use its "
                "focused_check; obey report_schema exactly and call delivery_tool once with those bounded "
                "fields. Do not use write_file/write_file_chunk for this report, never exceed max_output_bytes, and never add "
                "raw source dumps or exhaustive field/control lists. Runtime injects this as an authoritative "
                "_runtime_frontier_contract into each accepted investigation branch. For implementation "
                "candidates, choose exact owned files within the supplied root. "
                "Plan only the currently ready independent work, using concrete "
                "inputs already observed. Preserve original interfaces, dependencies and file "
                "ownership. Do not repeat completed work or invent missing inputs. Runtime "
                "will execute the branches and join them before you continue. Resource "
                "admission in this experiment uses a constant placeholder, not measured benefit.")
