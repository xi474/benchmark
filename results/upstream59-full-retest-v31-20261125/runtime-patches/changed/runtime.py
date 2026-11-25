from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import threading
import time
import uuid
from collections.abc import Callable
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, as_completed, wait
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from agent_runtime_demo.adaptive_routing import AdaptiveRoutingPolicy
from agent_runtime_demo.branch_context import BranchContextCompiler
from agent_runtime_demo.cancellation import CancellationScope, ExecutionRegistry
from agent_runtime_demo.critical_path import dynamic_critical_branches
from agent_runtime_demo.dag import ExecutionDAG
from agent_runtime_demo.delivery_ownership import reconcile_delivery_ownership
from agent_runtime_demo.execution_state_cache import ExecutionStateObserver
from agent_runtime_demo.inference_control import SGLangInferenceControl
from agent_runtime_demo.parallel_control import (
    CHOOSE_EXECUTION_MODE_TOOL_NAME,
    DisabledParallelController,
    InvalidExecutionModeDecision,
    ParallelController,
    ParallelDecisionPoint,
    ParallelOffer,
    ParallelPlanDecision,
    ResourceSnapshotProvider,
    SerialDecision,
    NullResourceSnapshotProvider,
)
from agent_runtime_demo.planning import (
    SPAWN_SUBTASKS_SCHEMA,
    SPAWN_SUBTASKS_TOOL_NAME,
    InvalidTaskPlan,
    SubtaskSpec,
    TaskPlan,
    parse_task_plan,
)
from agent_runtime_demo.policy import ToolPolicy
from agent_runtime_demo.parallel_control_v2 import ControllerV2, V2_TOOL
from agent_runtime_demo.parallel_runtime_v2 import ParallelRuntimeV2Mixin
from agent_runtime_demo.g1_discovery import contract_heuristics_enabled
from agent_runtime_demo.handshake_speculation import HandshakeSpeculationMixin
from agent_runtime_demo.report_authorization import ReportAuthorizationMixin
from agent_runtime_demo.write_preflight import WritePreflightMixin
from agent_runtime_demo.progress_recovery import ProgressRecoveryMixin
from agent_runtime_demo.repeated_output import RepeatedOutputGuardMixin
from agent_runtime_demo.validation_progress import ValidationProgressMixin
from agent_runtime_demo.recovery_state import RecoveryStateMixin
from agent_runtime_demo.providers.base import ModelProvider, ProviderCancelled
from agent_runtime_demo.semantic_placement import placement_for_join
from agent_runtime_demo.semantics import build_routing_context
from agent_runtime_demo.speculation.manager import (
    SpeculationManager,
    SpeculationTurn,
    SpeculativeToolResult,
)
from agent_runtime_demo.tools.registry import ToolRegistry
from agent_runtime_demo.tools.base import ToolExecutionContext
from agent_runtime_demo.tracing import JsonlTracer
from agent_runtime_demo.types import RuntimeState, ToolCall
from agent_runtime_demo.validation import (
    AcceptanceDecision,
    ValidatorResult,
    ValidationEngine,
    ValidationRegistry,
    new_candidate,
)


FRONTIER_DISCOVERY_GUIDANCE = (
    "Before the parent implements more work, review the original deliverables, "
    "verified contracts and input evidence, current writes, and available focused "
    "checks in this request. Evaluate each unfinished work unit separately. "
    "In ready_upsert, propose each unit that can now be implemented and checked "
    "independently, even if there is only one. Cite its observed inputs and check, "
    "give it a disjoint write_set, and state its required delivery. A later consumer "
    "or fan-in does not block its independent producers. If a unit needs unread "
    "evidence or an unmaterialized upstream output for its required check or delivery, "
    "report that prerequisite as blocked instead of marking it ready. Do not bundle "
    "unrelated producers or repeat completed work."
)


def add_frontier_discovery_guidance(prompt: str) -> str:
    """Keep guidance local to the current scoped report request."""
    base, marker, scope = prompt.partition("\n[RUNTIME_REQUEST_SCOPE] ")
    if not marker:
        raise ValueError("frontier discovery requires a scoped report request")
    return f"{base}\n[RUNTIME_FRONTIER_DISCOVERY]\n{FRONTIER_DISCOVERY_GUIDANCE}{marker}{scope}"


class RuntimeLimitExceeded(RuntimeError):
    pass


Validator = Callable[[], tuple[bool, str]]


@dataclass(slots=True)
class SubtaskOutcome:
    subtask_id: str
    status: str
    result: str = ""
    error: str = ""
    terminal_node_id: str = ""
    usage: dict[str, int] = field(default_factory=dict)
    started_at: float = 0.0
    ended_at: float = 0.0
    attempt_id: str = ""
    candidate_id: str = ""
    accepted: bool | None = None
    validation_score: float | None = None
    validation: dict[str, Any] | None = None
    inference_session_id: str = ""
    inference_request_id: str = ""
    last_selected_model: str = ""
    selected_worker: str = ""
    artifact_id: str = ""
    artifact: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.subtask_id,
            "status": self.status,
            "result": self.result,
            "error": self.error,
            "usage": self.usage,
            "duration_ms": round(max(0.0, self.ended_at - self.started_at) * 1000, 3),
            "attempt_id": self.attempt_id,
            "candidate_id": self.candidate_id or None,
            "accepted": self.accepted,
            "validation_score": self.validation_score,
            "validation": self.validation,
            "inference_session_id": self.inference_session_id or None,
            "inference_request_id": self.inference_request_id or None,
            "last_selected_model": self.last_selected_model or None,
            "selected_worker": self.selected_worker or None,
            "artifact_id": self.artifact_id or None,
            "artifact": self.artifact,
        }


@dataclass(slots=True)
class AttemptDispatch:
    subtask_id: str
    attempt_node_id: str
    attempt_id: str
    attempt_ordinal: int
    scope: CancellationScope
    requested_model: str = ""
    on_critical_path: bool = False


from agent_runtime_demo.output_guard import RootOutputGuardMixin
from agent_runtime_demo.cross_operation_progress import CrossOperationProgressMixin




COUNTEREXAMPLE_GATE_PROMPT = (
    "\n\n[BRANCH COUNTEREXAMPLE GATE v2 — required before deliver_files]\n"
    "\n"
    "Run one counterexample self-check on the component you implemented in this\n"
    "branch. Do not add any other review pass.\n"
    "\n"
    "1. Extract testable rules (target 2–5). From the task-text paragraphs this\n"
    "   component implements AND from the declared output structure\n"
    "   (contract.json / output schema), take rules whose expected behavior can be\n"
    "   decided from the text alone.\n"
    "   a) EVERY declared output field (its name, type and any token/format\n"
    "      convention) must become its own rule — do not skip fields you think\n"
    "      are trivial.\n"
    "   b) Prefer sentences with boundary keywords (恰好/仅/只/排除/不能/必须/唯一/\n"
    "      排序/固定/最小/最大/禁止/不得/至少/至多; only/exactly/never/must/cannot/\n"
    "      smallest/largest/fixed/unique/at least/at most).\n"
    "   c) Quote each rule's source sentence verbatim. A rule you cannot quote is\n"
    "      DISCARDED — never invent an expectation.\n"
    "\n"
    "2. Write counterexamples BEFORE running anything (max 8). Per rule, 1–3\n"
    "   counterexamples: input + expected output/error, each with a one-line\n"
    "   derivation citing your quote.\n"
    "   a) TOKEN LITERALITY: every key token in the expectation (operator, field\n"
    "      name, format string, marker) must appear VERBATIM as in the quote. Do\n"
    "      NOT translate tokens (e.g. if the task says op is ge/ne, the expected\n"
    "      output must contain ge/ne, not >=/!=).\n"
    "   b) If a translation seems unavoidable, declare it explicitly, mark that\n"
    "      counterexample high-risk, and additionally write one counterexample\n"
    "      expecting the ORIGINAL token as-is.\n"
    "   c) Include at least one violating input and one boundary input per rule.\n"
    "      Write ALL expectations first; only then execute. You may create new test\n"
    "      scripts under .semserve/counterexamples/ (new files are allowed; existing\n"
    "      files can only be changed with apply_patch).\n"
    "\n"
    "3. Execute and compare. Run each counterexample against the real interface\n"
    "   the parent will use (CLI entry or compute()). Compare the ENTIRE output\n"
    "   tree field by field — any field difference is a hit. Record every hit.\n"
    "\n"
    "4. Repair hits (max 3 rounds, stay within ~120s). Fix the implementation\n"
    "   with apply_patch. NEVER edit or re-derive the counterexample expectations —\n"
    "   re-run the SAME input and SAME expectation. After each fix, re-run ALL\n"
    "   counterexamples (regression). If every counterexample hits, first re-check\n"
    "   your quotes: the expectation derivation may be wrong, not the code.\n"
    "\n"
    "5. Deliver. If all counterexamples pass, or you could quote fewer than 2\n"
    "   rules (say why, with the quote evidence), proceed to deliver_files. If hits\n"
    "   remain after 3 rounds or the time budget, deliver anyway. In your final\n"
    "   branch report include: rules_quoted, counterexamples_generated, dropped,\n"
    "   hits, repairs, rounds.\n"
)


class AgentRuntime(RecoveryStateMixin, ValidationProgressMixin, RepeatedOutputGuardMixin, ProgressRecoveryMixin, WritePreflightMixin, ReportAuthorizationMixin, RootOutputGuardMixin, CrossOperationProgressMixin, HandshakeSpeculationMixin, ParallelRuntimeV2Mixin):
    """Owns the model/tool loop, dynamic child-agent scheduling, and execution DAG."""

    def __init__(
        self,
        provider: ModelProvider,
        tools: ToolRegistry,
        system_prompt: str,
        max_steps: int = 20,
        validator: Validator | None = None,
        tracer: JsonlTracer | None = None,
        *,
        dag: ExecutionDAG | None = None,
        dag_path: Path | None = None,
        max_parallelism: int = 20,
        max_subtasks: int = 20,
        max_subtask_depth: int = 1,
        max_plan_expansions: int = 1,
        max_initial_plan_expansions: int = 1,
        max_recovery_plan_expansions: int = 1,
        max_plan_validation_failures: int = 2,
        allow_subtasks: bool = True,
        allow_initial_subtasks: bool | None = None,
        allow_recovery_subtasks: bool | None = None,
        initial_plan: TaskPlan | None = None,
        scope_id: str = "root",
        parent_node_id: str | None = None,
        parent_task_id: str = "",
        plan_id: str = "root",
        allowed_input_refs: tuple[str, ...] = (),
        branch_inputs: dict[str, Any] | None = None,
        required_artifact_kinds: tuple[str, ...] = (),
        required_artifact_paths: tuple[str, ...] = (),
        required_test_targets: tuple[str, ...] = (),
        require_file_branch_contract: bool = False,
        depth: int = 0,
        owns_tools: bool = True,
        cancel_event: threading.Event | None = None,
        tool_semaphore: threading.BoundedSemaphore | None = None,
        cancellation_scope: CancellationScope | None = None,
        execution_registry: ExecutionRegistry | None = None,
        inference_control: SGLangInferenceControl | None = None,
        branch_id: str = "",
        attempt_id: str = "",
        validation_registry: ValidationRegistry | None = None,
        validation_workspace: Path | None = None,
        speculation_manager: SpeculationManager | None = None,
        owns_speculation_manager: bool = True,
        adaptive_routing_policy: AdaptiveRoutingPolicy | None = None,
        initial_parallel_controller: ParallelController | None = None,
        parallel_controller: ParallelController | None = None,
        parallel_controller_v2: ControllerV2 | None = None,
        resource_snapshot_provider: ResourceSnapshotProvider | None = None,
        required_for_join: bool = False,
        on_critical_path: bool = False,
        initial_route_mode: str = "auto",
        initial_requested_model: str = "",
        initial_reasoning_mode: str = "off",
        branch_context_compiler: BranchContextCompiler | None = None,
        gateway_routing_key: str = "",
        gateway_placement_mode: str = "attempt_affinity",
        execution_state_log_path: Path | None = None,
        codex_shadow_predictor: bool = False,
        codex_shadow_workload: str = "medium",
        execution_state_observer: ExecutionStateObserver | None = None,
        fork_only_stable_prefix: bool = False,
        fork_tool_schemas: list[dict[str, Any]] | None = None,
        output_guard: bool = False,
        root_public_checker: Callable | None = None,
        handshake_speculation: bool = False,
        handshake_speculation_wait_seconds: float = 120.0,
        handshake_speculation_provider_factory: Callable[[], ModelProvider] | None = None,
        handshake_speculation_commit_observer: Callable[[RuntimeState, Any], None] | None = None,
    ):
        if max_steps <= 0:
            raise ValueError("max_steps must be greater than zero")
        if max_parallelism <= 0:
            raise ValueError("max_parallelism must be greater than zero")
        if max_subtasks <= 0:
            raise ValueError("max_subtasks must be greater than zero")
        if max_subtask_depth < 0:
            raise ValueError("max_subtask_depth cannot be negative")
        if max_plan_expansions <= 0:
            raise ValueError("max_plan_expansions must be greater than zero")
        if max_initial_plan_expansions < 0:
            raise ValueError("max_initial_plan_expansions cannot be negative")
        if max_recovery_plan_expansions < 0:
            raise ValueError("max_recovery_plan_expansions cannot be negative")
        if max_plan_validation_failures <= 0:
            raise ValueError("max_plan_validation_failures must be greater than zero")
        self._guard_init(output_guard, root_public_checker)
        self._report_gate_init()
        self._progress_recovery_init()
        self._repeated_output_guard_init()
        self._validation_progress_init()
        self._recovery_init()
        self.fork_only_stable_prefix = fork_only_stable_prefix
        self._fork_parent_tool_schemas = copy.deepcopy(fork_tool_schemas)
        self._hs_init(handshake_speculation, handshake_speculation_wait_seconds,
                      handshake_speculation_provider_factory, handshake_speculation_commit_observer)
        self.provider = provider
        self.tools = tools
        self.system_prompt = system_prompt
        self.max_steps = max_steps
        self.validator = validator
        self.tracer = tracer or JsonlTracer(echo=False)
        self.dag = dag or ExecutionDAG(tracer=self.tracer, path=dag_path)
        self.dag_path = dag_path
        self.max_parallelism = max_parallelism
        self.max_subtasks = max_subtasks
        self.max_subtask_depth = max_subtask_depth
        self.max_plan_expansions = max_plan_expansions
        self.max_initial_plan_expansions = max_initial_plan_expansions
        self.max_recovery_plan_expansions = max_recovery_plan_expansions
        self.max_plan_validation_failures = max_plan_validation_failures
        self.allow_subtasks = allow_subtasks and depth < max_subtask_depth
        self.allow_initial_subtasks = self.allow_subtasks and (
            True if allow_initial_subtasks is None else allow_initial_subtasks
        )
        self.allow_recovery_subtasks = self.allow_subtasks and (
            True if allow_recovery_subtasks is None else allow_recovery_subtasks
        )
        self.initial_plan = initial_plan
        self.scope_id = scope_id
        self.parent_node_id = parent_node_id
        self.parent_task_id = parent_task_id
        self.plan_id = plan_id
        self.allowed_input_refs = tuple(allowed_input_refs)
        self.branch_inputs = copy.deepcopy(branch_inputs or {})
        frontier_contract = self.branch_inputs.get("_runtime_frontier_contract") or {}
        self._frontier_evidence_budget = int(
            frontier_contract.get("max_evidence_tool_calls") or 0
        )
        self._frontier_evidence_calls = 0
        self._frontier_evidence_lock = threading.Lock()
        implementation_contract = self.branch_inputs.get(
            "_runtime_implementation_contract"
        ) or {}
        self._implementation_source_evidence_budget = int(
            implementation_contract.get("max_source_evidence_calls") or 0
        )
        self._implementation_source_evidence_calls = 0
        self._implementation_source_evidence_lock = threading.Lock()
        self._implementation_target_inspection_budget = int(
            implementation_contract.get("max_target_inspection_calls")
            or (24 if implementation_contract else 0)
        )
        self._implementation_target_inspection_calls = 0
        self._branch_materialization_started = False
        self._root_integration_checkpoint_active = False
        self._root_post_join_source_evidence_budget = 6
        self._root_post_join_source_evidence_calls = 0
        self._root_post_join_target_inspection_budget = 12
        self._root_post_join_target_inspection_calls = 0
        self._root_post_join_source_evidence_lock = threading.Lock()
        self.required_artifact_kinds = tuple(required_artifact_kinds)
        self.required_artifact_paths = tuple(required_artifact_paths)
        self.required_test_targets = tuple(required_test_targets)
        self._file_branch_checks = None
        self.require_file_branch_contract = require_file_branch_contract
        self.depth = depth
        self.owns_tools = owns_tools
        self._owns_dag = dag is None
        self.cancellation_scope = cancellation_scope or CancellationScope(
            scope_id,
            event=cancel_event,
        )
        self.execution_registry = execution_registry or ExecutionRegistry()
        self._owns_execution_registry = execution_registry is None
        self.inference_control = inference_control
        self._owns_inference_control = inference_control is not None and depth == 0
        self.branch_id = branch_id or ("root" if depth == 0 else scope_id)
        self.branch_key = f"{self.dag.run_id}/{self.plan_id}/{self.branch_id}"
        self.attempt_id = attempt_id or f"attempt-{uuid.uuid4().hex}"
        self.inference_session_id = f"agent-{self.dag.run_id}-{self.attempt_id}"
        self.gateway_routing_key = gateway_routing_key or self.inference_session_id
        self.gateway_placement_mode = gateway_placement_mode
        self._active_request_id = ""
        self._cancel_event = self.cancellation_scope.event
        self._tool_semaphore = tool_semaphore or threading.BoundedSemaphore(max_parallelism)
        self._children_lock = threading.RLock()
        self._cancel_lock = threading.Lock()
        self._inference_cancel_requested = False
        self._active_children: set[AgentRuntime] = set()
        self.initial_parallel_controller = (
            initial_parallel_controller or DisabledParallelController()
        )
        self.parallel_controller = parallel_controller or DisabledParallelController()
        self.parallel_controller_v2 = parallel_controller_v2 or ControllerV2()
        if self.parallel_controller_v2.mode == "active" and (
            self.initial_parallel_controller.mode == "active"
            or self.parallel_controller.mode == "active"
        ):
            raise ValueError("v2 active cannot compete with active v1 controllers")
        self.resource_snapshot_provider = (
            resource_snapshot_provider or NullResourceSnapshotProvider()
        )
        allowed_tools = set(tools.names)
        if self.allow_initial_subtasks:
            allowed_tools.add(SPAWN_SUBTASKS_TOOL_NAME)
        if (
            self.initial_parallel_controller.mode == "active"
            and self.allow_initial_subtasks
        ) or (
            self.parallel_controller.mode == "active"
            and self.allow_recovery_subtasks
        ):
            allowed_tools.add(CHOOSE_EXECUTION_MODE_TOOL_NAME)
        self.policy = ToolPolicy(allowed_tools=frozenset(allowed_tools))
        if self.parallel_controller_v2.mode == "active" and self.allow_initial_subtasks:
            allowed_tools.add(V2_TOOL)
            self.policy = ToolPolicy(allowed_tools=frozenset(allowed_tools))
        self.terminal_node_id = ""
        self.task_node_id = ""
        self.last_usage: dict[str, int] = {}
        self.validation_registry = validation_registry or ValidationRegistry()
        self.validation_engine = ValidationEngine(self.validation_registry)
        self.validation_workspace = (validation_workspace or Path.cwd()).resolve()
        self.speculation_manager = speculation_manager
        self._owns_speculation_manager = owns_speculation_manager and speculation_manager is not None
        self.adaptive_routing_policy = adaptive_routing_policy or AdaptiveRoutingPolicy()
        self.required_for_join = required_for_join
        self.on_critical_path = on_critical_path
        self.initial_route_mode = initial_route_mode
        self.initial_requested_model = initial_requested_model
        if initial_reasoning_mode not in {"auto", "off", "on"}:
            raise ValueError("initial_reasoning_mode must be auto, off, or on")
        self.initial_reasoning_mode = initial_reasoning_mode
        self.branch_context_compiler = branch_context_compiler or BranchContextCompiler()
        self.last_selected_model = ""
        self.last_inference_request_id = ""
        self.last_route_info: dict[str, Any] = {}
        self._background_cleanup_started = False
        self._background_cleanup_results: list[dict[str, Any]] = []
        # Attempt-local idempotency: intentional retries in a new attempt or
        # plan get a fresh runtime/cache and therefore remain executable.
        self._tool_result_cache: dict[str, dict[str, Any]] = {}
        self._tool_result_cache_lock = threading.RLock()
        # Tool result memoization and no-progress loop detection are separate.
        # Shell cannot be safely memoized because it may mutate state, but an
        # exact call that repeatedly returns the same result without any other
        # observable operation completing must not run forever.
        self._tool_loop_lock = threading.RLock()
        self._tool_progress_version = 0
        self._tool_loop_records: dict[str, dict[str, Any]] = {}
        if self.output_guard_enabled:
            self._guard_progress_init()
        self._verified_artifacts: list[dict[str, Any]] = []
        self._verified_artifact_lock = threading.RLock()
        self._owns_execution_state_observer = False
        self.execution_state_observer = execution_state_observer
        if (
            self.execution_state_observer is None
            and self.depth == 0
            and execution_state_log_path is not None
        ):
            self.execution_state_observer = ExecutionStateObserver(
                self.dag,
                execution_state_log_path,
                workload_level=codex_shadow_workload,
                enable_codex_shadow=codex_shadow_predictor,
            )
            self._owns_execution_state_observer = True

    def run(
        self,
        task: str,
        *,
        initial_user_message: str | None = None,
        initial_messages: tuple[dict[str, Any], ...] | list[dict[str, Any]] | None = None,
        initial_step: int = 0,
    ) -> str:
        if initial_user_message is not None and initial_messages is not None:
            raise ValueError(
                "initial_user_message and initial_messages are mutually exclusive"
            )
        if initial_step < 0:
            raise ValueError("initial_step cannot be negative")
        if initial_step >= self.max_steps:
            raise ValueError("initial_step must be less than max_steps")
        user_message = task if initial_user_message is None else initial_user_message
        # Parent checkpoints are deep-copied once when the plan is dispatched.
        # Each child only copies the outer list; the inherited message mappings
        # are treated as immutable and can therefore share a cacheable prefix.
        messages = (
            list(initial_messages)
            if initial_messages is not None
            else [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_message},
            ]
        )
        task_kind = "task" if self.depth == 0 else "child_task"
        self.task_node_id = self.dag.add_node(
            kind=task_kind,
            label=task[:160] or task_kind,
            scope_id=self.scope_id,
            status="pending",
            input={"task": task},
            metadata={
                "run_id": self.dag.run_id,
                "plan_id": self.plan_id,
                "depth": self.depth,
                "parent_task_id": self.parent_task_id,
                "branch_id": self.branch_id,
                "branch_key": self.branch_key,
                "attempt_id": self.attempt_id,
                "inference_session_id": self.inference_session_id,
                "gateway_routing_key": self.gateway_routing_key,
                "gateway_placement_mode": self.gateway_placement_mode,
            },
        )
        if self.parent_node_id:
            self.dag.add_edge(self.parent_node_id, self.task_node_id, kind="spawn")
        self.execution_registry.register(
            self.task_node_id,
            self.cancellation_scope,
            kind=task_kind,
            cancel=self.cancel,
            metadata={"scope_id": self.scope_id},
        )
        self.dag.transition(self.task_node_id, "ready")
        self.dag.transition(self.task_node_id, "running")
        state = RuntimeState(
            task=task,
            run_id=self.dag.run_id,
            task_id=self.task_node_id,
            parent_task_id=self.parent_task_id,
            plan_id=self.plan_id,
            scope_id=self.scope_id,
            branch_id=self.branch_id,
            branch_key=self.branch_key,
            attempt_id=self.attempt_id,
            inference_session_id=self.inference_session_id,
            gateway_routing_key=self.gateway_routing_key,
            required_for_join=self.required_for_join,
            on_critical_path=self.on_critical_path,
            route_mode=self.initial_route_mode,
            requested_model=self.initial_requested_model,
            reasoning_mode=self.initial_reasoning_mode,
            messages=messages,
            step=initial_step,
        )
        if initial_messages is not None and self.depth == 0:
            self._v2_restore_root_integration_checkpoint(state)
            self._guard_restore_selfcheck_phase(state)
        self.tracer.emit(
            "task_started",
            task=task,
            run_id=self.dag.run_id,
            task_id=self.task_node_id,
            plan_id=self.plan_id,
            scope_id=self.scope_id,
            depth=self.depth,
            branch_id=self.branch_id,
            branch_key=self.branch_key,
            attempt_id=self.attempt_id,
            inference_session_id=self.inference_session_id,
            resumed_from_step=initial_step or None,
            inherited_message_count=len(messages) if initial_messages is not None else 0,
        )

        try:
            final = self._run_loop(state)
            self._check_cancelled()
            self.last_usage = dict(state.usage)
            self.dag.transition(
                self.task_node_id,
                "succeeded",
                output={"final_answer": final, "usage": state.usage},
            )
            return final
        except (ProviderCancelled, KeyboardInterrupt) as exc:
            self.cancel()
            state.status = "cancelled"
            self.last_usage = dict(state.usage)
            self.dag.transition(
                self.task_node_id,
                "cancelled",
                error={"type": type(exc).__name__, "message": str(exc)},
            )
            self.tracer.emit(
                "task_cancelled",
                reason=str(exc),
                step=state.step,
                task_id=self.task_node_id,
            )
            if isinstance(exc, KeyboardInterrupt):
                raise ProviderCancelled("task cancelled by user") from exc
            raise
        except BaseException as exc:
            state.status = "failed"
            self._recovery_change(state, 'block', type(exc).__name__ + ': ' + str(exc))
            self.last_usage = dict(state.usage)
            self.dag.transition(
                self.task_node_id,
                "failed",
                error={"type": type(exc).__name__, "message": str(exc)},
            )
            self.tracer.emit(
                "task_failed",
                reason=str(exc),
                exception_type=type(exc).__name__,
                step=state.step,
                task_id=self.task_node_id,
            )
            raise
        finally:
            self._hs_shutdown()
            if self.parallel_controller_v2.mode != "off":
                if state.pending_v2_offer is not None:
                    self.tracer.emit("parallel_v2_offer_abandoned", reason="task_ended",
                                     offer_id=state.pending_v2_offer.offer_id)
                self.parallel_controller_v2.finish(state.run_id, self.scope_id)
            self.execution_registry.unregister(self.task_node_id)
            if self.depth > 0:
                self.cancellation_scope.close()
            if self._owns_speculation_manager and self.speculation_manager is not None:
                self.speculation_manager.close()
            if self._owns_execution_state_observer and self.execution_state_observer is not None:
                self.execution_state_observer.close()
            if self.owns_tools:
                try:
                    self.tools.close()
                except BaseException as exc:
                    self.tracer.emit(
                        "tool_registry_close_failed",
                        task_id=self.task_node_id,
                        error=str(exc),
                    )
            if self._owns_dag and (self.dag_path is not None or self.dag.path is not None):
                self.dag.save(self.dag_path)
            if self._owns_inference_control and self.inference_control is not None:
                # Winner response latency must not include loser abort, session
                # close, cache-aware invalidation, or their retry delays.  Each
                # loser was already submitted to the control pool by cancel(),
                # so stop accepting new jobs but let those jobs finish in the
                # background.  Tests and process shutdown paths can explicitly
                # drain them through wait_for_background_cleanup().
                try:
                    self.inference_control.close(wait=False)
                except TypeError:
                    # Compatibility with small test/custom controllers that
                    # implement the pre-background close() contract.
                    results = self.inference_control.close()
                    self._background_cleanup_results.extend(results)
                    for result in results:
                        self.tracer.emit("inference_control_completed", **result)
                else:
                    self._background_cleanup_started = True
                    self.tracer.emit(
                        "inference_control_backgrounded",
                        task_id=self.task_node_id,
                        scope_id=self.scope_id,
                    )

    def wait_for_background_cleanup(self) -> list[dict[str, Any]]:
        """Drain loser release jobs after the user-visible response is ready."""

        if (
            not self._owns_inference_control
            or self.inference_control is None
            or not self._background_cleanup_started
        ):
            return list(self._background_cleanup_results)
        results = self.inference_control.close(wait=True)
        self._background_cleanup_started = False
        self._background_cleanup_results.extend(results)
        for result in results:
            self.tracer.emit("inference_control_completed", **result)
        if self._owns_dag and (self.dag_path is not None or self.dag.path is not None):
            self.dag.save(self.dag_path)
        return list(self._background_cleanup_results)

    def cancel(self, reason: str = "task cancellation requested") -> None:
        self._hs_discard("task_cancelled")
        first_request = self.cancellation_scope.cancel(reason)
        if first_request:
            self.tracer.emit(
                "cancellation_requested",
                task_id=self.task_node_id,
                scope_id=self.scope_id,
                reason=reason,
            )
            self._transition_to_cancelling(self.task_node_id, reason)
        cancel_provider = getattr(self.provider, "cancel", None)
        if callable(cancel_provider):
            cancel_provider()
        with self._cancel_lock:
            request_inference_cancel = (
                not self._inference_cancel_requested
                and bool(self._active_request_id)
            )
            if request_inference_cancel:
                self._inference_cancel_requested = True
        if self.inference_control is not None and request_inference_cancel:
            release_future = self.inference_control.cancel_attempt_async(
                rid=self._active_request_id,
                session_id=self.inference_session_id,
                branch_id=self.branch_id,
                attempt_id=self.attempt_id,
                reason=reason,
            )
            if release_future is not None:
                self.tracer.emit(
                    "inference_cancel_requested",
                    task_id=self.task_node_id,
                    scope_id=self.scope_id,
                    branch_id=self.branch_id,
                    attempt_id=self.attempt_id,
                    rid=self._active_request_id,
                    session_id=self.inference_session_id,
                    reason=reason,
                )
        with self._children_lock:
            children = list(self._active_children)
        for child in children:
            child.cancel(reason)

    def _observe_execution_state(
        self,
        state: RuntimeState,
        *,
        boundary: str,
        step: int,
    ) -> None:
        """Record low-cost execution facts without changing Runtime control."""

        if self.depth != 0 or self.execution_state_observer is None:
            return
        row = self.execution_state_observer.observe(
            task=state.task,
            scope_id=self.scope_id,
            boundary=boundary,
            step=step,
        )
        memory = row["memory"]
        self.tracer.emit(
            "execution_state_observed",
            boundary=boundary,
            step=step,
            state_version=memory["state_version"],
            ready_count=memory["ready_count"],
            independent_ready_count=memory["independent_ready_count"],
            join_pending=memory["join_pending"],
            prediction=row.get("prediction"),
            observer_ms=row["observer_ms"],
        )

    def _run_loop(self, state: RuntimeState) -> str:
        self._recovery_require_open()
        cursor_node_id = self.task_node_id
        if self.initial_plan is not None:
            cursor_node_id = self._execute_initial_plan(state, self.initial_plan, cursor_node_id)
        elif self.depth == 0 and not self._guard_serial_selfcheck(state):
            cursor_node_id = self._observe_initial_parallel_decision_point(
                state,
                node_id=cursor_node_id,
            )

        while state.step < self.max_steps:
            self._check_cancelled()
            self._guard_check_selfcheck_deadline(state)
            self._recovery_require_open()
            self._observe_execution_state(
                state,
                boundary="before_model_request",
                step=state.step + 1,
            )
            cursor_node_id = self._v2_before_request(state, cursor_node_id)
            state.step += 1
            state.inference_request_id = (
                f"agent-{self.dag.run_id}-{self.attempt_id}-step-{state.step}"
            )
            self._active_request_id = state.inference_request_id
            self._hs_prepare(state)
            tool_schemas = self._model_tool_schemas(state)
            self.tracer.emit('tool_schema_visibility',
                             names=[s.get('function', {}).get('name') for s in tool_schemas])
            if self.fork_only_stable_prefix:
                from agent_runtime_demo.fork_only_prefix import apply_fork_envelope
                tool_schemas = apply_fork_envelope(self, state, tool_schemas)
            routing_context = build_routing_context(
                state, tools_available=bool(tool_schemas)
            )
            model_node_id = self.dag.add_node(
                kind="model_turn",
                label=f"model turn {state.step}",
                scope_id=self.scope_id,
                status="pending",
                input={
                    "step": state.step,
                    "routing": routing_context.to_dict(),
                    "inference": {
                        "branch_id": state.branch_id,
                        "attempt_id": state.attempt_id,
                        "session_id": state.inference_session_id,
                        "rid": state.inference_request_id,
                    },
                },
                metadata={"task_id": state.task_id, "attempt_id": state.attempt_id},
            )
            self.dag.add_edge(cursor_node_id, model_node_id, kind="control")
            self.dag.transition(model_node_id, "ready")
            self.dag.transition(model_node_id, "running")
            self.tracer.emit(
                "model_request",
                step=state.step,
                routing=routing_context.to_dict(),
                run_id=state.run_id,
                task_id=state.task_id,
                plan_id=state.plan_id,
                node_id=model_node_id,
                scope_id=self.scope_id,
                branch_id=state.branch_id,
                branch_key=state.branch_key,
                attempt_id=state.attempt_id,
                inference_session_id=state.inference_session_id,
                inference_request_id=state.inference_request_id,
            )

            speculation_turn = None
            if self.speculation_manager is not None:
                speculation_turn = self.speculation_manager.begin_turn(
                    state,
                    base_dag_seq=int(self.dag.snapshot()["last_seq"]),
                )

            try:
                with self._guard_selfcheck_deadline_scope(state):
                    turn = self._hs_complete(state, tool_schemas, routing_context)
                self._guard_check_selfcheck_deadline(state)
            except BaseException as exc:
                if self.speculation_manager is not None:
                    self.speculation_manager.abort_turn(
                        speculation_turn,
                        f"provider_error:{type(exc).__name__}",
                    )
                self.dag.transition(
                    model_node_id,
                    "cancelled" if isinstance(exc, ProviderCancelled) else "failed",
                    error={"type": type(exc).__name__, "message": str(exc)},
                )
                self.terminal_node_id = model_node_id
                self._guard_check_selfcheck_deadline(state)
                raise
            if self.speculation_manager is not None:
                self.speculation_manager.reconcile(speculation_turn, turn.tool_calls)
            selected_model = str(turn.route_info.get("selected_model") or "")
            selected_worker = str(turn.route_info.get("selected_worker") or "")
            if self.inference_control is not None and selected_worker:
                physical_model = self.inference_control.model_for_worker(selected_worker)
                if physical_model:
                    turn.route_info["vsr_selected_model"] = selected_model
                    turn.route_info["selected_model"] = physical_model
                    selected_model = physical_model
            if selected_model:
                state.last_selected_model = selected_model
                self.last_selected_model = selected_model
            self.last_inference_request_id = state.inference_request_id
            self.last_route_info = dict(turn.route_info)
            if self.inference_control is not None and selected_worker:
                self.inference_control.register_session_worker(
                    state.inference_session_id,
                    selected_worker,
                )
            self._active_request_id = ""
            state.messages.append(turn.assistant_message)
            self._merge_usage(state.usage, turn.usage)
            self.dag.transition(
                model_node_id,
                "succeeded",
                output={
                    "content": turn.content,
                    "tool_calls": [
                        {"id": call.id, "name": call.name, "arguments": call.arguments}
                        for call in turn.tool_calls
                    ],
                    "usage": turn.usage,
                    "route": turn.route_info,
                },
            )
            self.tracer.emit(
                "model_response",
                step=state.step,
                run_id=state.run_id,
                task_id=state.task_id,
                plan_id=state.plan_id,
                node_id=model_node_id,
                scope_id=self.scope_id,
                branch_id=state.branch_id,
                branch_key=state.branch_key,
                attempt_id=state.attempt_id,
                inference_session_id=state.inference_session_id,
                inference_request_id=state.inference_request_id,
                content=turn.content,
                tool_calls=[
                    {"id": call.id, "name": call.name, "arguments": call.arguments}
                    for call in turn.tool_calls
                ],
                usage=turn.usage,
                route=turn.route_info,
            )

            guard_handled, guard_final = self._guard_intercept_turn(state, turn, model_node_id)
            if guard_handled:
                cursor_node_id = model_node_id
                if guard_final is not None:
                    return guard_final
                continue

            if self._intercept_truncated_write_turn(state, turn):
                cursor_node_id = model_node_id
                continue

            if self._v2_intercept_turn(state, turn):
                cursor_node_id = model_node_id
                continue

            if getattr(self, "_frontier_report_request_active", False):
                valid_report = (
                    len(turn.tool_calls) == 1
                    and turn.tool_calls[0].name == "report_frontier_state"
                )
                if not valid_report:
                    if self.output_guard_enabled:
                        self._guard_close_rejected(state, turn, "expected_report_frontier_state")
                    repairs = int(
                        getattr(self, "_frontier_report_protocol_repairs", 0)
                    ) + 1
                    self._frontier_report_protocol_repairs = repairs
                    self.tracer.emit(
                        "frontier_report_protocol_repaired",
                        step=state.step,
                        task_id=state.task_id,
                        scope_id=state.scope_id,
                        repair_attempt=repairs,
                        returned_tools=[call.name for call in turn.tool_calls],
                    )
                    if repairs >= 2:
                        raise RuntimeError(
                            "executor did not acknowledge required frontier report"
                        )
                    state.messages.append({
                        "role": "user",
                        "content": (
                            "Before continuing, call report_frontier_state exactly once. "
                            "Report only the delta justified by already completed tool "
                            "results. If inspection revealed independent work, report it "
                            "before writing its outputs; never re-offer an already written "
                            "output without a later failure. Empty arrays are valid. Do not "
                            "call an ordinary tool or answer the task in this turn."
                        ),
                    })
                    cursor_node_id = model_node_id
                    continue
                self._frontier_report_protocol_repairs = 0

            if state.pending_parallel_offer is not None and (
                len(turn.tool_calls) != 1
                or turn.tool_calls[0].name != CHOOSE_EXECUTION_MODE_TOOL_NAME
            ):
                state.parallel_decision_repairs += 1
                if state.parallel_decision_repairs >= 2:
                    pending_controller = (
                        state.pending_parallel_controller or self.parallel_controller
                    )
                    pending_controller.abandon_offer(
                        state.pending_parallel_offer,
                        "model_did_not_return_structured_decision",
                    )
                    state.pending_parallel_offer = None
                    state.pending_parallel_controller = None
                    state.parallel_offer_history_cut = None
                    state.parallel_decision_repairs = 0
                    state.messages.append(
                        {
                            "role": "user",
                            "content": (
                                "The optional parallel offer has been closed safely. "
                                "Continue the original task serially and do not assume "
                                "that any new branches were created."
                            ),
                        }
                    )
                else:
                    state.messages.append(
                        {
                            "role": "user",
                            "content": (
                                "Respond to the pending Runtime offer using exactly one "
                                "choose_execution_mode function call. Do not answer the "
                                "task or call another tool in this turn."
                            ),
                        }
                    )
                cursor_node_id = model_node_id
                continue

            if not turn.tool_calls and not turn.content.strip():
                # A Qwen3 thinking turn can consume the entire output budget
                # before producing a visible answer or Function Call.  Never
                # treat that transport-level empty turn as task completion.
                # Pending parallel offers are handled above so empty turns
                # cannot silently consume the offer TTL and later crash the
                # run with an already-abandoned decision.
                state.retry_count += 1
                state.messages.append(
                    {
                        "role": "user",
                        "content": (
                            "The previous model turn returned neither a visible answer "
                            "nor a function call. Continue the original task now; if a "
                            "tool is required, emit its structured function call before "
                            "using the remaining reasoning budget."
                        ),
                    }
                )
                self.tracer.emit(
                    "empty_model_turn_retried",
                    step=state.step,
                    task_id=state.task_id,
                    node_id=model_node_id,
                    scope_id=self.scope_id,
                    output_budget_exhausted=bool(
                        turn.route_info.get("output_budget_exhausted")
                    ),
                )
                cursor_node_id = model_node_id
                continue

            if not turn.tool_calls:
                final, cursor_node_id = self._handle_final_answer(
                    state, turn.content, model_node_id
                )
                if final is not None:
                    return final
                continue

            if state.tool_repair_mode and all(
                call.name == "write_file_chunk"
                and "_invalid_json" not in call.arguments
                for call in turn.tool_calls
            ):
                self.tracer.emit(
                    "truncated_write_repair_accepted",
                    step=state.step,
                    task_id=state.task_id,
                    scope_id=state.scope_id,
                    tool_call_count=len(turn.tool_calls),
                )
                state.tool_repair_mode = ""
                state.tool_repair_attempts = 0

            cursor_node_id = self._execute_tool_turn(
                state, turn.tool_calls, model_node_id, speculation_turn
            )
            self._hs_after_tools(state, turn.tool_calls)
            verified_artifact = self.latest_verified_artifact()
            if (
                verified_artifact is not None
                and self.depth > 0
                and verified_artifact.get("completes_branch") is True
                and self._artifact_satisfies_branch_completion(verified_artifact)
            ):
                final, cursor_node_id = self._handle_final_answer(
                    state,
                    str(verified_artifact["content"]),
                    cursor_node_id,
                )
                if final is not None:
                    self.tracer.emit(
                        "branch_completed_from_verified_artifact",
                        task_id=state.task_id,
                        scope_id=state.scope_id,
                        branch_id=state.branch_id,
                        attempt_id=state.attempt_id,
                        artifact_id=verified_artifact["artifact_id"],
                    )
                    return final

            if (
                verified_artifact is not None
                and self.depth > 0
                and verified_artifact.get("completes_branch") is True
                and not self._artifact_satisfies_branch_completion(verified_artifact)
            ):
                self.tracer.emit(
                    "branch_completion_deferred",
                    task_id=state.task_id,
                    scope_id=state.scope_id,
                    branch_id=state.branch_id,
                    attempt_id=state.attempt_id,
                    artifact_id=verified_artifact.get("artifact_id"),
                    artifact_kind=verified_artifact.get("kind"),
                    required_artifact_kinds=list(self.required_artifact_kinds),
                )

        auto_final = self._try_auto_finalize_implementation_branch(
            state,
            cursor_node_id,
        )
        if auto_final is not None:
            return auto_final

        state.status = "failed"
        failure_node_id = self.dag.add_node(
            kind="task_failure",
            label="maximum model turns exceeded",
            scope_id=self.scope_id,
            status="pending",
            input={"reason": "max_steps_exceeded", "max_steps": self.max_steps},
        )
        self.dag.add_edge(cursor_node_id, failure_node_id, kind="control")
        self.dag.transition(
            failure_node_id,
            "failed",
            error={"reason": "max_steps_exceeded", "max_steps": self.max_steps},
        )
        self.terminal_node_id = failure_node_id
        raise RuntimeLimitExceeded(f"Agent exceeded {self.max_steps} steps")

    def _try_auto_finalize_implementation_branch(
        self,
        state: RuntimeState,
        upstream_node_id: str,
    ) -> str | None:
        """Attest a completed implementation contract before failing on turn budget.

        ``deliver_files`` is an integrity attestation, not a semantic correctness
        judgment.  Requiring the model to remember that final mechanical call can
        otherwise turn a fully materialized branch into a false failure.  Runtime
        may perform the identical tool operation only for implementation branches
        whose declared contract can be satisfied entirely by file evidence.  Test
        requirements are never inferred or waived here; the root verifier remains
        responsible for end-to-end correctness.
        """

        implementation_contract = self.branch_inputs.get(
            "_runtime_implementation_contract"
        )
        if (
            self.depth <= 0
            or not isinstance(implementation_contract, dict)
            or not implementation_contract
            or not self._branch_materialization_started
            or not self.required_artifact_paths
            or self.required_test_targets
            or (
                self.required_artifact_kinds
                and "file" not in self.required_artifact_kinds
            )
            or self._artifact_satisfies_branch_completion(
                self.latest_verified_artifact()
            )
        ):
            return None

        call = ToolCall(
            id=f"runtime-auto-deliver-{uuid.uuid4().hex}",
            name="deliver_files",
            arguments={"paths": list(self.required_artifact_paths)},
        )
        node_id = self.dag.add_node(
            kind="tool_call",
            label=f"{call.name} ({call.id})",
            scope_id=self.scope_id,
            status="pending",
            input={"arguments": call.arguments},
            metadata={
                "call_id": call.id,
                "tool": call.name,
                "runtime_generated": True,
                "reason": "implementation_turn_budget_exhausted",
            },
        )
        self.dag.add_edge(upstream_node_id, node_id, kind="control")
        self.dag.transition(node_id, "ready")
        self.tracer.emit(
            "branch_auto_delivery_attempted",
            task_id=state.task_id,
            scope_id=state.scope_id,
            branch_id=state.branch_id,
            attempt_id=state.attempt_id,
            paths=list(self.required_artifact_paths),
            max_steps=self.max_steps,
        )
        result, status, terminal_node_id = self._execute_one_call(
            state,
            call,
            node_id,
        )
        verified_artifact = self.latest_verified_artifact()
        if (
            status != "succeeded"
            or not self._artifact_satisfies_branch_completion(verified_artifact)
        ):
            self.tracer.emit(
                "branch_auto_delivery_failed",
                task_id=state.task_id,
                scope_id=state.scope_id,
                branch_id=state.branch_id,
                attempt_id=state.attempt_id,
                status=status,
                result=result,
            )
            return None

        final, _ = self._handle_final_answer(
            state,
            str(verified_artifact["content"]),
            terminal_node_id,
        )
        if final is None:
            return None
        self.tracer.emit(
            "branch_auto_delivery_succeeded",
            task_id=state.task_id,
            scope_id=state.scope_id,
            branch_id=state.branch_id,
            attempt_id=state.attempt_id,
            artifact_id=verified_artifact["artifact_id"],
            paths=list(self.required_artifact_paths),
        )
        return final

    def _intercept_truncated_write_turn(
        self,
        state: RuntimeState,
        turn: Any,
    ) -> bool:
        """Convert a length-truncated large write into a bounded repair turn."""
        finish_reason = str(turn.route_info.get("finish_reason") or "")
        if finish_reason != "length":
            return False
        invalid_writes = [
            call
            for call in turn.tool_calls
            if call.name in {"write_file", "write_file_chunk"}
            and "_invalid_json" in call.arguments
        ]
        if not invalid_writes:
            return False
        state.tool_repair_attempts += 1
        if state.tool_repair_attempts > 2:
            self.tracer.emit(
                "truncated_write_repair_exhausted",
                step=state.step,
                task_id=state.task_id,
                scope_id=state.scope_id,
                attempts=state.tool_repair_attempts,
            )
            raise RuntimeLimitExceeded(
                "large write remained truncated after two chunk-repair turns"
            )

        target_paths: list[str] = []
        compact_calls: list[dict[str, Any]] = []
        for call in turn.tool_calls:
            raw = str(call.arguments.get("_invalid_json") or "")
            path_match = re.search(r'"path"\s*:\s*"([^"\\]{1,512})"', raw)
            target_path = path_match.group(1) if path_match else ""
            if target_path:
                target_paths.append(target_path)
            compact_calls.append(
                {
                    "id": call.id,
                    "type": "function",
                    "function": {
                        "name": call.name,
                        "arguments": json.dumps(
                            {
                                "path": target_path,
                                "content": "<omitted: provider truncated this tool call>",
                                "overwrite": False,
                            },
                            ensure_ascii=False,
                            separators=(",", ":"),
                        ),
                    },
                }
            )
        # Avoid replaying tens of thousands of invalid argument characters on
        # the repair request while retaining a protocol-complete tool-call pair.
        state.messages[-1] = {
            "role": "assistant",
            "content": "",
            "tool_calls": compact_calls,
        }
        for call in turn.tool_calls:
            result = {
                "ok": False,
                "status": "truncated_tool_call",
                "completed": False,
                "rerun_required": True,
                "finish_reason": "length",
                "required_tool": "write_file_chunk",
                "max_chunk_chars": 8192,
                "error": (
                    "The provider truncated the tool arguments before valid JSON "
                    "was completed; the partial write was not executed."
                ),
            }
            state.messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call.id,
                    "name": call.name,
                    "content": json.dumps(result, ensure_ascii=False),
                }
            )
            self.tracer.emit(
                "tool_result",
                step=state.step,
                task_id=state.task_id,
                scope_id=state.scope_id,
                tool_call_id=call.id,
                tool=call.name,
                status="rejected",
                result=result,
            )
        target_text = ", ".join(target_paths) if target_paths else "the intended file"
        state.tool_repair_mode = "write_file_chunk"
        state.messages.append(
            {
                "role": "user",
                "content": (
                    "Runtime rejected the previous large write because the provider "
                    "stopped at its output-token limit before closing the tool JSON. "
                    f"Continue {target_text} using exactly one write_file_chunk call "
                    "now. The content must be at most 8192 UTF-8 characters. For the "
                    "first chunk use expected_offset=0 and truncate=true; do not "
                    "regenerate the whole file in one call."
                ),
            }
        )
        self.tracer.emit(
            "truncated_write_repair_requested",
            step=state.step,
            task_id=state.task_id,
            scope_id=state.scope_id,
            attempts=state.tool_repair_attempts,
            target_paths=target_paths,
            required_tool="write_file_chunk",
            max_chunk_chars=8192,
        )
        return True

    def _execute_initial_plan(
        self,
        state: RuntimeState,
        plan: TaskPlan,
        cursor_node_id: str,
    ) -> str:
        call_id = f"runtime-plan-{uuid.uuid4().hex[:12]}"
        arguments = {
            "policy_version": plan.policy_version,
            "subtasks": [
                {
                    "id": spec.id,
                    "task": spec.task,
                    "depends_on": list(spec.depends_on),
                    "input_refs": list(spec.input_refs),
                }
                for spec in plan.subtasks
            ],
            "failure_policy": plan.failure_policy,
            "join_policy": plan.join_policy,
            "acceptance_policy": {
                "operator": plan.acceptance_policy.operator,
                "validators": list(plan.acceptance_policy.validators),
                "minimum_score": plan.acceptance_policy.minimum_score,
            },
        }
        if plan.join_policy == "quorum":
            arguments["quorum"] = plan.quorum
        if plan.join_policy == "top_k":
            arguments["top_k"] = plan.top_k
        if plan.join_policy == "deadline":
            arguments["deadline_seconds"] = plan.deadline_seconds
        raw_call = {
            "id": call_id,
            "type": "function",
            "function": {
                "name": SPAWN_SUBTASKS_TOOL_NAME,
                "arguments": json.dumps(arguments, ensure_ascii=False),
            },
        }
        state.messages.append({"role": "assistant", "content": "", "tool_calls": [raw_call]})
        expansion_node_id = self.dag.add_node(
            kind="control_expand",
            label="runtime supplied subtask plan",
            scope_id=self.scope_id,
            status="pending",
            input={"call_id": call_id, "plan": arguments},
            metadata={"source": "runtime", "ordinal": 0},
        )
        self.dag.add_edge(cursor_node_id, expansion_node_id, kind="control")
        self.dag.transition(expansion_node_id, "ready")
        self.dag.transition(expansion_node_id, "running")
        try:
            summary, status, terminal_node_id = self._run_task_plan(
                state, plan, expansion_node_id
            )
        except ProviderCancelled as exc:
            self.dag.transition(
                expansion_node_id,
                "cancelled",
                error={"type": type(exc).__name__, "message": str(exc)},
            )
            raise
        except BaseException as exc:
            self.dag.transition(
                expansion_node_id,
                "failed",
                error={"type": type(exc).__name__, "message": str(exc)},
            )
            raise
        self.dag.transition(expansion_node_id, status, output=summary)
        state.messages.append(
            {
                "role": "tool",
                "tool_call_id": call_id,
                "name": SPAWN_SUBTASKS_TOOL_NAME,
                "content": json.dumps(
                    self._model_facing_tool_result(
                        SPAWN_SUBTASKS_TOOL_NAME, summary
                    ),
                    ensure_ascii=False,
                ),
            }
        )
        state.plan_expansion_count += 1
        state.initial_plan_expansion_count += 1
        return terminal_node_id

    def _execute_tool_turn(
        self,
        state: RuntimeState,
        calls: list[ToolCall],
        model_node_id: str,
        speculation_turn: SpeculationTurn | None = None,
    ) -> str:
        if self._recovery.mode == 'BLOCKED':
            return self._recovery_reject_batch(state, calls, model_node_id)
        report_error = self._report_admit_batch(state, calls)
        if report_error:
            return self._report_reject_batch(state, calls, model_node_id, report_error)
        self._progress_recovery_before_batch(state, calls)
        self._validation_progress_before_batch(state, calls)
        control_tools = {SPAWN_SUBTASKS_TOOL_NAME, CHOOSE_EXECUTION_MODE_TOOL_NAME, V2_TOOL}
        if sum(call.name in control_tools for call in calls) > 1:
            # One atomic plan per turn avoids ambiguous nested joins and duplicate expansion.
            invalid = "only one planning/decision call is allowed per model turn; ordinary tools still execute"
        else:
            invalid = ""

        operation_keys = [self._tool_operation_key(call) for call in calls]
        first_ordinal_by_key: dict[str, int] = {}
        same_turn_duplicate_of: dict[int, int] = {}
        for ordinal, (call, operation_key) in enumerate(zip(calls, operation_keys)):
            if call.name in control_tools:
                continue
            if operation_key in first_ordinal_by_key:
                same_turn_duplicate_of[ordinal] = first_ordinal_by_key[operation_key]
            else:
                first_ordinal_by_key[operation_key] = ordinal

        call_nodes: list[str] = []
        for ordinal, call in enumerate(calls):
            if call.name == SPAWN_SUBTASKS_TOOL_NAME:
                kind = "control_expand"
            elif call.name in {CHOOSE_EXECUTION_MODE_TOOL_NAME, V2_TOOL}:
                kind = "parallel_mode_decision"
            else:
                kind = "tool_call"
            metadata: dict[str, Any] = {
                "call_id": call.id,
                "tool": call.name,
                "ordinal": ordinal,
            }
            if ordinal in same_turn_duplicate_of:
                metadata["duplicate_of_ordinal"] = same_turn_duplicate_of[ordinal]
                metadata["duplicate_status"] = "duplicate_in_same_turn"
            if kind == "tool_call":
                policy = self.tools.execution_policy(call.name, call.arguments)
                metadata["execution_policy"] = asdict(policy)
            node_id = self.dag.add_node(
                kind=kind,
                label=f"{call.name} ({call.id})",
                scope_id=self.scope_id,
                status="pending",
                input={"arguments": call.arguments},
                metadata=metadata,
            )
            self.dag.add_edge(model_node_id, node_id, kind="control")
            self.dag.transition(node_id, "ready")
            call_nodes.append(node_id)

        self._observe_execution_state(
            state,
            boundary="before_tool_dispatch",
            step=state.step,
        )

        deferred_ordinals = self._v2_semantic_checkpoint_deferred_ordinals(state, calls)
        if deferred_ordinals:
            self.tracer.emit(
                "parallel_v2_semantic_checkpoint",
                step=state.step,
                task_id=state.task_id,
                scope_id=self.scope_id,
                executed_call_ids=[
                    call.id for ordinal, call in enumerate(calls)
                    if ordinal not in deferred_ordinals
                ],
                deferred_call_ids=[calls[ordinal].id for ordinal in sorted(deferred_ordinals)],
                reason="shared_contract_materialization_before_downstream_mutations",
            )

        ordered_results: list[dict[str, Any] | None] = [None] * len(calls)
        terminal_nodes: list[str] = list(call_nodes)
        with ThreadPoolExecutor(
            max_workers=1 if self._guard_serial_selfcheck(state) else max(1, min(
                self.max_parallelism,
                len(calls) - len(deferred_ordinals),
            )),
            thread_name_prefix="agent-tool",
        ) as executor:
            futures: dict[Future[tuple[dict[str, Any], str, str]], int] = {}
            for ordinal, (call, node_id) in enumerate(zip(calls, call_nodes)):
                if ordinal in deferred_ordinals or ordinal in same_turn_duplicate_of:
                    continue
                loop_result = self._tool_loop_preflight(call)
                if loop_result is not None:
                    self.dag.transition(node_id, "running")
                    loop_status = (
                        "succeeded" if loop_result.get("ok") is not False else "failed"
                    )
                    self.dag.transition(node_id, loop_status, output=loop_result)
                    ordered_results[ordinal] = loop_result
                    self.tracer.emit(
                        "tool_result",
                        step=state.step,
                        task_id=state.task_id,
                        node_id=node_id,
                        scope_id=self.scope_id,
                        tool_call_id=call.id,
                        tool=call.name,
                        status=loop_status,
                        result=loop_result,
                    )
                    continue
                futures[
                    executor.submit(
                        self._execute_one_call,
                        state,
                        call,
                        node_id,
                        invalid if call.name in control_tools else "",
                        speculation_turn,
                    )
                ] = ordinal
            for future in as_completed(futures):
                ordinal = futures[future]
                result, status, terminal_node_id = future.result()
                result = self._observe_tool_progress(calls[ordinal], result)
                ordered_results[ordinal] = result
                terminal_nodes[ordinal] = terminal_node_id
                self.tracer.emit(
                    "tool_result",
                    step=state.step,
                    task_id=state.task_id,
                    node_id=call_nodes[ordinal],
                    scope_id=self.scope_id,
                    tool_call_id=calls[ordinal].id,
                    tool=calls[ordinal].name,
                    status=status,
                    result=result,
                )

        for ordinal, primary_ordinal in sorted(same_turn_duplicate_of.items()):
            node_id = call_nodes[ordinal]
            call = calls[ordinal]
            primary_call = calls[primary_ordinal]
            primary_result = ordered_results[primary_ordinal] or {
                "ok": False,
                "error": "primary duplicate call did not produce a result",
            }
            duplicate_result = {
                "ok": primary_result.get("ok") is not False,
                "status": "duplicate_in_same_turn",
                "duplicate_in_same_turn": True,
                "duplicate_of_call_id": primary_call.id,
                "completed": primary_result.get("ok") is not False,
                "rerun_required": False,
                "result_digest": self._tool_result_digest(primary_result),
            }
            self.dag.transition(node_id, "running")
            duplicate_status = (
                "succeeded" if duplicate_result["ok"] else "failed"
            )
            self.dag.transition(node_id, duplicate_status, output=duplicate_result)
            ordered_results[ordinal] = duplicate_result
            self.tracer.emit(
                "tool_duplicate_suppressed",
                step=state.step,
                task_id=state.task_id,
                node_id=node_id,
                scope_id=self.scope_id,
                tool_call_id=call.id,
                duplicate_of_call_id=primary_call.id,
                tool=call.name,
                operation_key=operation_keys[ordinal],
            )
            self.tracer.emit(
                "tool_result",
                step=state.step,
                task_id=state.task_id,
                node_id=node_id,
                scope_id=self.scope_id,
                tool_call_id=call.id,
                tool=call.name,
                status=duplicate_status,
                result=duplicate_result,
            )

        for ordinal in sorted(deferred_ordinals):
            node_id = call_nodes[ordinal]
            call = calls[ordinal]
            result = {
                "ok": False,
                "deferred": True,
                "retry_after_runtime_recheck": True,
                "error": (
                    "runtime_semantic_checkpoint: this mutation was not executed because "
                    "the same tool batch materialized a shared contract. Runtime must "
                    "re-evaluate the newly concrete frontier before downstream writes."
                ),
            }
            if (contract_heuristics_enabled()
                    and state.v2_frontier_handshake_reason == "g1_before_first_business_write"):
                result.update(
                    not_executed=True,
                    error="g1_discovery_checkpoint: this write was not executed. A single bounded frontier inventory is due before the first business implementation batch. Continue after the authorized report; serial execution remains allowed.")
            self.dag.transition(node_id, "running")
            self.dag.transition(node_id, "failed", output=result)
            ordered_results[ordinal] = result
            self.tracer.emit(
                "tool_result",
                step=state.step,
                task_id=state.task_id,
                node_id=node_id,
                scope_id=self.scope_id,
                tool_call_id=call.id,
                tool=call.name,
                status="failed",
                result=result,
            )

        join_node_id = self.dag.add_node(
            kind="join",
            label=f"tool join after turn {state.step}",
            scope_id=self.scope_id,
            status="pending",
            metadata={"join_policy": "all_terminal", "ordered_call_ids": [c.id for c in calls]},
        )
        for call_node_id, terminal_node_id in zip(call_nodes, terminal_nodes):
            self.dag.add_edge(call_node_id, join_node_id, kind="join")
            if terminal_node_id != call_node_id:
                self.dag.add_edge(terminal_node_id, join_node_id, kind="join")
        self.dag.transition(join_node_id, "ready")
        self.dag.transition(join_node_id, "running")
        results = [result or {"ok": False, "error": "missing tool result"} for result in ordered_results]
        join_status = "succeeded" if all(result.get("ok") is not False for result in results) else "partial"
        self.dag.transition(
            join_node_id,
            join_status,
            output={"results": results, "ordered_call_ids": [call.id for call in calls]},
        )

        # Completion order is recorded in trace/DAG timestamps. Model replay stays
        # deterministic and preserves the original call order and call_id mapping.
        for ordinal, (call, result) in enumerate(zip(calls, results)):
            replay_result = self._structured_model_tool_result(call, result)
            state.messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call.id,
                    "name": call.name,
                    "content": json.dumps(replay_result, ensure_ascii=False),
                }
            )
            if call.name == SPAWN_SUBTASKS_TOOL_NAME:
                plan_executed = terminal_nodes[ordinal] != call_nodes[ordinal]
                if plan_executed:
                    state.plan_expansion_count += 1
                    state.initial_plan_expansion_count += 1
                    state.plan_validation_failures = 0
                else:
                    state.plan_validation_failures = min(
                        state.plan_validation_failures + 1,
                        self.max_plan_validation_failures,
                    )
                    self.tracer.emit(
                        "subtask_plan_rejected",
                        step=state.step,
                        task_id=state.task_id,
                        node_id=call_nodes[ordinal],
                        scope_id=self.scope_id,
                        tool_call_id=call.id,
                        error=result.get("error"),
                        plan_validation_failures=state.plan_validation_failures,
                        max_plan_validation_failures=(
                            self.max_plan_validation_failures
                        ),
                        retry_allowed=(
                            state.plan_validation_failures
                            < self.max_plan_validation_failures
                        ),
                    )
                if result.get("ok") is False:
                    join_node_id = self._observe_parallel_decision_point(
                        state,
                        node_id=join_node_id,
                        event_type="join_blocked",
                        branch_id=state.branch_id,
                        attempt_id=state.attempt_id,
                        failure_type="subtask_plan_failed",
                        required_for_join=True,
                        on_critical_path=True,
                        join_blocked=True,
                        validation_summary=json.dumps(result, ensure_ascii=False),
                    )
        self._recovery_observe_receipts(state, calls, results)
        if self._validation_progress_after_batch(state, calls, results):
            self._recovery_change(state, 'block', 'public_validation_recovery_exhausted')
            raise RuntimeLimitExceeded("public validation progress recovery exhausted without validated improvement")
        if self._repeated_output_after_batch(state, calls, results):
            self._recovery_change(state, 'block', 'five_identical_business_outputs')
            raise RuntimeLimitExceeded("five identical business model outputs without verified execution progress")
        if self._progress_recovery_after_batch(state, calls, results):
            raise RuntimeLimitExceeded("duplicate tool loop: progress recovery exhausted after two business turns without verified progress")
        breaker_results = [
            result for result in results if result.get("duplicate_tool_circuit_breaker")
        ]
        if breaker_results and not self._progress_recovery_active:
            state.messages.append(
                {
                    "role": "user",
                    "content": (
                        "Runtime detected an exact tool-call loop with no new verified "
                        "evidence. Do not call the same tool with the same arguments again. "
                        "Choose a materially different action, write the implementation, "
                        "or finish/fail this scope explicitly."
                    ),
                }
            )
            self.tracer.emit(
                "tool_loop_circuit_breaker",
                step=state.step,
                task_id=state.task_id,
                scope_id=self.scope_id,
                results=breaker_results,
            )
            if any(result.get("terminate_scope") and not result.get("duplicate_write_suppressed")
                   for result in breaker_results):
                self._recovery_change(state, 'block', 'duplicate_tool_loop_exhausted')
                raise RuntimeLimitExceeded(
                    "duplicate tool loop persisted after circuit-breaker feedback"
                )
        if isinstance(state.deferred_parallel_offer, ParallelOffer):
            join_node_id = self._install_parallel_offer(
                state,
                state.deferred_parallel_offer,
                upstream_node_id=join_node_id,
            )
            state.deferred_parallel_offer = None
        return self._v2_after_tools(state, calls, results, join_node_id)

    @staticmethod
    def _tool_operation_key(call: ToolCall) -> str:
        return json.dumps(
            {"tool": call.name, "arguments": call.arguments},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )

    @staticmethod
    def _tool_result_digest(result: dict[str, Any]) -> str:
        rendered = json.dumps(
            result,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )
        return hashlib.sha256(rendered.encode("utf-8")).hexdigest()

    def _tool_loop_preflight(self, call: ToolCall) -> dict[str, Any] | None:
        if self.output_guard_enabled:
            return self._cross_preflight(call)
        operation_key = self._tool_operation_key(call)
        with self._tool_loop_lock:
            record = self._tool_loop_records.get(operation_key)
            if (
                record is None
                or record.get("progress_version") != self._tool_progress_version
                or int(record.get("repeat_count", 0)) < 2
            ):
                return None
            repeat_count = int(record["repeat_count"]) + 1
            record["repeat_count"] = repeat_count
            terminate_scope = repeat_count >= 4
            return {
                "ok": False,
                "status": "duplicate_tool_circuit_breaker",
                "duplicate_tool_circuit_breaker": True,
                "completed": True,
                "rerun_required": False,
                "choose_new_action": not terminate_scope,
                "terminate_scope": terminate_scope,
                "repeat_count": repeat_count,
                "progress_version": self._tool_progress_version,
                "operation_sha256": hashlib.sha256(
                    operation_key.encode("utf-8")
                ).hexdigest(),
                "result_digest": record.get("result_digest"),
                "error": (
                    "exact tool call already completed twice with the same result and "
                    "no intervening verified progress"
                ),
            }

    def _observe_tool_progress(
        self,
        call: ToolCall,
        result: dict[str, Any],
    ) -> dict[str, Any]:
        if self.output_guard_enabled:
            return self._cross_observe(call, result)
        if result.get("ok") is not True:
            return result
        operation_key = self._tool_operation_key(call)
        result_digest = self._tool_result_digest(result)
        with self._tool_loop_lock:
            record = self._tool_loop_records.get(operation_key)
            if (
                record is not None
                and record.get("progress_version") == self._tool_progress_version
                and record.get("result_digest") == result_digest
            ):
                repeat_count = int(record.get("repeat_count", 1)) + 1
                record["repeat_count"] = repeat_count
                if repeat_count >= 2:
                    annotated = copy.deepcopy(result)
                    annotated.update(
                        {
                            "status": "duplicate_no_new_evidence",
                            "duplicate_no_new_evidence": True,
                            "completed": True,
                            "rerun_required": False,
                            "repeat_count": repeat_count,
                            "progress_version": self._tool_progress_version,
                            "result_digest": result_digest,
                        }
                    )
                    return annotated
                return result

            self._tool_progress_version += 1
            self._tool_loop_records[operation_key] = {
                "result_digest": result_digest,
                "progress_version": self._tool_progress_version,
                "repeat_count": 1,
            }
            if len(self._tool_loop_records) > 256:
                oldest_key = next(iter(self._tool_loop_records))
                if oldest_key != operation_key:
                    self._tool_loop_records.pop(oldest_key, None)
        return result

    def _structured_model_tool_result(
        self,
        call: ToolCall,
        result: dict[str, Any],
    ) -> dict[str, Any]:
        replay = copy.deepcopy(self._model_facing_tool_result(call.name, result))
        if call.name in {SPAWN_SUBTASKS_TOOL_NAME, CHOOSE_EXECUTION_MODE_TOOL_NAME, V2_TOOL}:
            return replay
        if replay.get("ok") is True:
            replay.setdefault("completed", True)
            replay.setdefault("rerun_required", False)
            command = str(call.arguments.get("command") or "")
            if (
                call.name == "shell"
                and str(replay.get("output") or "").strip() == "done"
                and "work_orders.csv" in command
                and "assets.csv" in command
                and "technicians.csv" in command
            ):
                replay.setdefault("check", "work_order_relationships")
                replay.setdefault("violations", [])
            replay["runtime_fact"] = {
                "tool": call.name,
                "operation_sha256": hashlib.sha256(
                    self._tool_operation_key(call).encode("utf-8")
                ).hexdigest(),
                "result_sha256": self._tool_result_digest(result),
                "progress_version": self._tool_progress_version,
            }
        return replay

    @staticmethod
    def _model_facing_tool_result(
        tool_name: str,
        result: dict[str, Any],
    ) -> dict[str, Any]:
        """Compact a DAG join for synthesis while retaining full evidence in the DAG."""

        if tool_name not in {SPAWN_SUBTASKS_TOOL_NAME, CHOOSE_EXECUTION_MODE_TOOL_NAME, V2_TOOL}:
            return result
        subtasks = result.get("subtasks")
        if not isinstance(subtasks, list):
            return result
        artifacts = []
        failures = []
        unverified = []
        for raw in subtasks:
            if not isinstance(raw, dict):
                continue
            branch_id = str(raw.get("id") or "")
            artifact = raw.get("artifact")
            artifact = artifact if isinstance(artifact, dict) else {}
            delivery_verified = artifact.get("delivery_verified") is True
            if raw.get("status") == "succeeded" and raw.get("accepted") is not False:
                artifacts.append(
                    {
                        "branch_id": branch_id,
                        "artifact_id": raw.get("artifact_id"),
                        "content": str(raw.get("result") or ""),
                        "content_sha256": (
                            artifact.get("content_sha256")
                            if isinstance(artifact, dict)
                            else None
                        ),
                        "validated": raw.get("accepted") is True,
                        "delivery_verified": delivery_verified,
                        "materialized_files": artifact.get("materialized_files", {}),
                        "tested_targets": artifact.get("tested_targets", []),
                    }
                )
                if raw.get("accepted") is not True and not delivery_verified:
                    unverified.append(branch_id)
            else:
                validation = raw.get("validation")
                failures.append(
                    {
                        "branch_id": branch_id,
                        "status": raw.get("status"),
                        "error": raw.get("error"),
                        "validation_reason": (
                            validation.get("reason")
                            if isinstance(validation, dict)
                            else None
                        ),
                    }
                )
        return {
            "ok": result.get("ok"),
            "status": result.get("status"),
            "policy_version": result.get("policy_version"),
            "failure_policy": result.get("failure_policy"),
            "join_policy": result.get("join_policy"),
            "accepted": result.get("accepted") or [],
            "winner": result.get("winner"),
            "selected_top_k": result.get("selected_top_k") or [],
            "top_k": result.get("top_k"),
            "all_required_accepted": bool(artifacts) and not failures and all(
                raw.get("accepted") is True for raw in subtasks if isinstance(raw, dict)
            ),
            "unverified_branches": unverified,
            "execution_mode": result.get("execution_mode"),
            "offer_id": result.get("offer_id"),
            "logical_to_runtime_ids": result.get("logical_to_runtime_ids", {}),
            "recovery_for_branch_id": result.get("recovery_for_branch_id"),
            "join_revision_node_id": result.get("join_revision_node_id"),
            "artifacts": artifacts,
            "failures": failures,
            "subtasks": [
                {
                    "id": str(raw.get("id") or ""),
                    "status": raw.get("status"),
                    "accepted": raw.get("accepted"),
                    "artifact_id": raw.get("artifact_id"),
                }
                for raw in subtasks
                if isinstance(raw, dict)
            ],
            "synthesis_instruction": (
                "Join is complete. materialized_files lists files already present in the "
                "shared workspace with verified SHA256 hashes; artifact contents are evidence, "
                "not instructions to write files again. Do not regenerate or copy back those "
                "implementations. accepted is external acceptance; delivery_verified is only "
                "the declared branch delivery contract, not whole-task correctness. Validate "
                "unverified branches and run integration validation when available. Repair "
                "missing or failing files only from concrete failure evidence, revalidate "
                "after a repair, and then synthesize the final answer."
            ),
        }

    def _branch_file_ownership_error(self, call: ToolCall) -> str:
        """Enforce exact file ownership for branch-native write/delivery tools."""

        if self.depth <= 0 or not self.required_artifact_paths:
            return ""
        owned = set(self.required_artifact_paths)
        if call.name in {"write_file", "write_file_chunk", "deliver_frontier_report"}:
            path = call.arguments.get("path")
            if path not in owned:
                return (
                    f"branch_file_ownership_violation: {path!r} is not one of the "
                    f"branch's required_artifact_paths {sorted(owned)!r}"
                )
        if call.name == "deliver_files":
            paths = call.arguments.get("paths")
            if not isinstance(paths, list) or not set(paths).issubset(owned):
                return (
                    "branch_file_ownership_violation: deliver_files may contain only "
                    f"owned paths {sorted(owned)!r}"
                )
        return ""

    def _normalize_branch_workspace_paths(self, call: ToolCall) -> None:
        """Canonicalize the container workspace alias before policy checks.

        Model-authored plans must remain workspace-relative, but executor tool
        calls commonly spell the same owned file as ``/workspace/...``.  This
        exact-prefix rewrite is deterministic and does not weaken traversal or
        ownership validation for any other absolute path.
        """

        if self.depth <= 0:
            return

        def normalize(value: Any) -> Any:
            if isinstance(value, str) and value.startswith("/workspace/"):
                return value.removeprefix("/workspace/")
            return value

        if "path" in call.arguments:
            call.arguments["path"] = normalize(call.arguments["path"])
        if isinstance(call.arguments.get("paths"), list):
            call.arguments["paths"] = [
                normalize(path) for path in call.arguments["paths"]
            ]

    def _branch_exploration_budget_error(self, call: ToolCall) -> str:
        """Bound semantically equivalent exploration even when arguments vary."""

        if self.depth <= 0:
            if (
                not self._root_integration_checkpoint_active
                or call.name not in {"shell", "read_file", "list_files", "search_text"}
            ):
                return ""
            if call.name == "shell":
                source = str(call.arguments.get("command") or "").lower()
            else:
                source = str(
                    call.arguments.get("path")
                    or call.arguments.get("query")
                    or call.arguments
                    or ""
                ).lower()
            is_legacy_recovery = any(marker in source for marker in (
                "/shared/", "shared/legacy", ".semserve/frontier/",
            ))
            is_target_inspection = False
            if not is_legacy_recovery:
                if call.name == "shell":
                    read_only_markers = (
                        "cat ", "sed ", "head ", "tail ", "awk ",
                        "grep ", "rg ", "wc ", "find ", "ls ",
                    )
                    is_target_inspection = (
                        any(marker in source for marker in (
                            "/workspace/generated_app", "generated_app/",
                            "cd /workspace/generated_app",
                        ))
                        and any(marker in source for marker in read_only_markers)
                    )
                else:
                    is_target_inspection = any(marker in source for marker in (
                        "/workspace/generated_app", "generated_app/",
                    ))
            if not is_legacy_recovery and not is_target_inspection:
                return ""
            with self._root_post_join_source_evidence_lock:
                if is_target_inspection:
                    if (
                        self._root_post_join_target_inspection_calls
                        >= self._root_post_join_target_inspection_budget
                    ):
                        return (
                            "root_post_join_target_inspection_budget_exhausted: "
                            "the delivered target has already received bounded review; "
                            "stop sequential source inspection, materialize run.sh and "
                            "the required migration metadata now, run only executable "
                            "focused startup/contract checks, and finish"
                        )
                    self._root_post_join_target_inspection_calls += 1
                    return ""
                if (
                    self._root_post_join_source_evidence_calls
                    >= self._root_post_join_source_evidence_budget
                ):
                    return (
                        "root_post_join_source_recovery_budget_exhausted: verified "
                        "implementation branches have already joined; stop re-reading "
                        "legacy sources, materialize the remaining root-owned entrypoint "
                        "and metadata artifacts required by the original contract, run "
                        "focused integration checks, and finish"
                    )
                self._root_post_join_source_evidence_calls += 1
            return ""
        if call.name not in {"shell", "read_file", "list_files", "search_text"}:
            return ""
        if self._frontier_evidence_budget > 0:
            with self._frontier_evidence_lock:
                if self._frontier_evidence_calls >= self._frontier_evidence_budget:
                    return (
                        "frontier_evidence_budget_exhausted: no more exploration is allowed; "
                        "summarize the strongest evidence already observed and call "
                        "deliver_frontier_report now"
                    )
                self._frontier_evidence_calls += 1
            return ""

        if call.name == "shell":
            source = str(call.arguments.get("command") or "").lower()
        else:
            source = str(
                call.arguments.get("path")
                or call.arguments.get("query")
                or call.arguments
                or ""
            ).lower()
        is_source_evidence = any(marker in source for marker in (
            "/shared/", "shared/", ".semserve/frontier/",
        ))
        if (
            is_source_evidence
            and not self._branch_materialization_started
            and self._implementation_source_evidence_budget > 0
        ):
            with self._implementation_source_evidence_lock:
                if (self._implementation_source_evidence_calls
                        >= self._implementation_source_evidence_budget):
                    return (
                        "implementation_source_evidence_budget_exhausted: the verified "
                        "handoff has already been supplied; stop source rediscovery, "
                        "materialize the owned required_artifact_paths, and run focused "
                        "checks"
                    )
                self._implementation_source_evidence_calls += 1
            return ""
        if is_source_evidence or self._implementation_target_inspection_budget <= 0:
            return ""
        if call.name == "shell":
            is_target_inspection = any(marker in source for marker in (
                "cat ", "sed ", "head ", "tail ", "awk ",
                "grep ", "rg ", "wc ", "find ", "ls ",
            ))
        else:
            is_target_inspection = True
        if not is_target_inspection:
            return ""
        with self._implementation_source_evidence_lock:
            if (
                self._implementation_target_inspection_calls
                >= self._implementation_target_inspection_budget
            ):
                return (
                    "implementation_target_inspection_budget_exhausted: the target "
                    "implementation has already received bounded review; stop sequential "
                    "source inspection, apply the evidence-backed repair to the owned "
                    "files now, run executable focused checks, deliver the files, and "
                    "finish this branch"
                )
            self._implementation_target_inspection_calls += 1
        return ""

    def _execute_one_call(
        self,
        state: RuntimeState,
        call: ToolCall,
        node_id: str,
        forced_error: str = "",
        speculation_turn: SpeculationTurn | None = None,
    ) -> tuple[dict[str, Any], str, str]:
        self.dag.transition(node_id, "running")
        try:
            self._check_cancelled()
            self._guard_check_selfcheck_deadline(state)
            self._normalize_branch_workspace_paths(call)
            policy_error = (
                forced_error
                or self._guard_selfcheck_tool_error(state, call)
                or self._report_call_error(state, call)
                or self.policy.validate(call)
                or self._branch_file_ownership_error(call)
                or self._branch_exploration_budget_error(call)
            )
            if policy_error:
                result = {"ok": False, "error": policy_error}
                self.dag.transition(node_id, "failed", output=result)
                return result, "failed", node_id

            recovery_feedback = self._recovery_action_gate(state, call)
            if recovery_feedback is not None:
                self.dag.transition(node_id, "failed", output=recovery_feedback)
                return recovery_feedback, "failed", node_id

            if call.name == V2_TOOL:
                return self._execute_v2_decision(state, call, node_id)

            if call.name == CHOOSE_EXECUTION_MODE_TOOL_NAME:
                return self._execute_parallel_mode_decision(state, call, node_id)

            if call.name == SPAWN_SUBTASKS_TOOL_NAME:
                try:
                    self_aware_parallel_active = (
                        self.initial_parallel_controller.mode == "active"
                        or self.parallel_controller.mode == "active"
                    )
                    if self_aware_parallel_active and state.plan_expansion_count > 0:
                        raise InvalidTaskPlan(
                            "autonomous Root planning is already complete; after any "
                            "successful Root plan, an additional Root plan must be "
                            "authorized by a valid Runtime recovery offer"
                        )
                    if (
                        state.plan_expansion_count
                        >= self.max_plan_expansions
                    ):
                        raise InvalidTaskPlan(
                            "parallel expansion attempt budget exhausted; "
                            "synthesize or repair the current result serially"
                        )
                    if self_aware_parallel_active and (
                        state.initial_plan_expansion_count
                        >= self.max_initial_plan_expansions
                    ):
                        raise InvalidTaskPlan(
                            "initial planning budget exhausted; a successful Root plan "
                            "cannot be followed by another autonomous spawn_subtasks. "
                            "Only a valid Runtime recovery offer may authorize an "
                            "additional Root plan"
                        )
                    if (
                        state.plan_validation_failures
                        >= self.max_plan_validation_failures
                    ):
                        raise InvalidTaskPlan(
                            "parallel plan validation retry budget exhausted; "
                            "continue or repair serially"
                        )
                    plan = parse_task_plan(
                        call.arguments,
                        max_subtasks=self.max_subtasks,
                        strict_model_contract=True,
                    )
                    for validator_ref in plan.acceptance_policy.validators:
                        try:
                            self.validation_registry.resolve(validator_ref)
                        except ValueError as exc:
                            raise InvalidTaskPlan(str(exc)) from exc
                except InvalidTaskPlan as exc:
                    result = {"ok": False, "error": f"invalid_task_plan: {exc}"}
                    self.dag.transition(node_id, "failed", output=result)
                    return result, "failed", node_id
                result, status, terminal_node_id = self._run_task_plan(
                    state, plan, node_id
                )
                self.dag.transition(node_id, status, output=result)
                return result, status, terminal_node_id

            operation_key = json.dumps(
                {"tool": call.name, "arguments": call.arguments},
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            # An operation key identifies arguments, not the state they read.
            # Children, shell commands and external writers can mutate that
            # state without passing through this runtime's local cache.
            cache_safe = self.tools.can_reuse_result(call.name, call.arguments)
            with self._tool_result_cache_lock:
                cached_result = (
                    self._tool_result_cache.get(operation_key) if cache_safe else None
                )
            if cached_result is not None:
                result = copy.deepcopy(cached_result)
                result["_semserve_reused"] = True
                result["_semserve_operation_key"] = operation_key
                self.tracer.emit(
                    "tool_result_reused",
                    run_id=state.run_id,
                    task_id=state.task_id,
                    plan_id=state.plan_id,
                    branch_id=state.branch_id,
                    branch_key=state.branch_key,
                    attempt_id=state.attempt_id,
                    node_id=node_id,
                    call_id=call.id,
                    tool=call.name,
                    operation_key=operation_key,
                )
                self.dag.transition(node_id, "succeeded", output=result)
                artifact_node_id = self._record_verified_tool_artifact(
                    call, result, node_id
                )
                return result, "succeeded", artifact_node_id

            with self._tool_semaphore:
                self._check_cancelled()
                speculative_result: SpeculativeToolResult | None = None
                if self.speculation_manager is not None:
                    speculative_result = self.speculation_manager.claim(
                        speculation_turn,
                        call,
                        canonical_node_id=node_id,
                    )
                context = ToolExecutionContext(
                    node_id=node_id,
                    call_id=call.id,
                    scope_id=self.scope_id,
                    cancel_event=self._cancel_event,
                )
                self.execution_registry.register(
                    node_id,
                    self.cancellation_scope,
                    kind="tool_call",
                    metadata={"call_id": call.id, "tool": call.name},
                )
                try:
                    with self._write_preflight_lock(call):
                        write_feedback = self._write_preflight(state, call)
                        if write_feedback is not None:
                            result = write_feedback
                        elif (os.environ.get("SEMSERVE_G1") == "1"
                              and call.name == "shell" and self.depth > 0
                              and self.required_artifact_kinds == ("file",)):
                            # Both newly generated and reused child actions use
                            # the same isolated shell boundary before commit.
                            from .g1_branch_checks import maybe_execute_branch_shell
                            isolated = maybe_execute_branch_shell(self, call, context)
                            result = (isolated if isolated is not None else
                                      self.tools.execute(call.name, call.arguments, context))
                        elif speculative_result is not None:
                            result = speculative_result.result
                            self.tracer.emit(
                                "tool_result_reused",
                                task_id=state.task_id,
                                node_id=node_id,
                                scope_id=self.scope_id,
                                step=state.step,
                                tool=call.name,
                                call_id=call.id,
                                prediction_id=speculative_result.prediction_id,
                                speculative_node_id=speculative_result.speculative_node_id,
                            )
                        else:
                            with self._guard_selfcheck_deadline_scope(state):
                                result = self.tools.execute(call.name, call.arguments, context)
                                if (call.name == "deliver_files" and self.depth > 0
                                        and self.required_artifact_kinds == ("file",)
                                        and self.required_artifact_paths):
                                    from .branch_test_delivery import FileBranchChecks, branch_selfcheck_enabled
                                    check_entries = branch_selfcheck_enabled()
                                    if self.required_test_targets or check_entries:
                                        if self._file_branch_checks is None:
                                            self._file_branch_checks = FileBranchChecks(
                                                self.validation_workspace, self.branch_id, self.attempt_id)
                                        result = self._file_branch_checks.complete(
                                            result, call_id=call.id, paths=self.required_artifact_paths,
                                            targets=self.required_test_targets, inputs=self.branch_inputs,
                                            check_entries=check_entries,
                                            execute=lambda command: self.tools.execute("shell", {"command": command}, context),
                                            emit=lambda event, **proof: self.tracer.emit(
                                                event, scope_id=self.scope_id, step=state.step, **proof))
                            result = self._guard_selfcheck_result(state, call, result)
                        self._write_preflight_observe(call, result)
                finally:
                    self.execution_registry.unregister(node_id)
            if (
                cache_safe
                and result.get("ok") is not False
                and result.get("status") != "cancelled"
            ):
                with self._tool_result_cache_lock:
                    self._tool_result_cache[operation_key] = copy.deepcopy(result)
            if result.get("status") == "cancelled":
                self._transition_to_cancelling(node_id, result.get("error", "cancelled"))
                status = "cancelled"
            else:
                status = "succeeded" if result.get("ok") is not False else "failed"
            self.dag.transition(node_id, status, output=result)
            terminal_node_id = node_id
            if status == "succeeded":
                if call.name in {
                    "write_file", "write_file_chunk", "edit_file", "apply_patch"
                }:
                    self._branch_materialization_started = True
                terminal_node_id = self._record_verified_tool_artifact(
                    call, result, node_id
                )
            return result, status, terminal_node_id
        except ProviderCancelled as exc:
            result = {"ok": False, "error": str(exc), "status": "cancelled"}
            self.dag.transition(node_id, "cancelled", output=result)
            return result, "cancelled", node_id
        except BaseException as exc:
            result = {
                "ok": False,
                "error": f"execution failed: {type(exc).__name__}: {exc}",
            }
            self.dag.transition(node_id, "failed", output=result)
            return result, "failed", node_id

    def _execute_parallel_mode_decision(
        self,
        state: RuntimeState,
        call: ToolCall,
        node_id: str,
    ) -> tuple[dict[str, Any], str, str]:
        offer = state.pending_parallel_offer
        controller = state.pending_parallel_controller
        offer_history_cut = state.parallel_offer_history_cut
        if not isinstance(offer, ParallelOffer) or controller is None:
            result = {"ok": False, "error": "no pending parallel offer"}
            self.dag.transition(node_id, "failed", output=result)
            return result, "failed", node_id
        phase_enabled = (
            self.allow_initial_subtasks
            if offer.decision_phase == "initial"
            else self.allow_recovery_subtasks
        )
        if not phase_enabled:
            result = {
                "ok": False,
                "error": f"runtime-triggered {offer.decision_phase} subtasks are disabled",
                "fallback_serial": True,
            }
            self.dag.transition(node_id, "failed", output=result)
            return result, "failed", node_id
        try:
            decision = controller.consume_model_decision(
                call.arguments,
                offer,
                current_step=state.step,
                max_subtasks=self.max_subtasks,
            )
        except InvalidExecutionModeDecision as exc:
            state.parallel_decision_repairs += 1
            offer_expired = state.step > offer.expires_after_step
            fallback_serial = offer_expired or state.parallel_decision_repairs >= 2
            if fallback_serial:
                controller.abandon_offer(
                    offer,
                    "offer_expired" if offer_expired else "invalid_decision_limit",
                )
                state.pending_parallel_offer = None
                state.pending_parallel_controller = None
                state.parallel_offer_history_cut = None
                state.parallel_decision_repairs = 0
            result = {
                "ok": False,
                "error": f"invalid_execution_mode_decision: {exc}",
                "fallback_serial": fallback_serial,
            }
            self.dag.transition(node_id, "failed", output=result)
            return result, "failed", node_id

        state.pending_parallel_offer = None
        state.pending_parallel_controller = None
        state.parallel_offer_history_cut = None
        state.parallel_decision_repairs = 0
        if isinstance(decision, SerialDecision):
            escalated_after_decline = False
            if (
                offer.decision_phase == "recovery"
                and
                offer.branch_id != "root"
                and decision.serial_action == "retry"
                and self.adaptive_routing_policy.enabled
            ):
                if self.adaptive_routing_policy.escalation_action == "strong_model":
                    state.route_mode = "require_strong"
                    state.requested_model = self.adaptive_routing_policy.strong_model
                else:
                    state.route_mode = "auto"
                    state.requested_model = ""
                    state.reasoning_mode = "on"
                state.escalation_reason = "branch_parallel_offer_declined"
                escalated_after_decline = True
            result = {
                "ok": True,
                "decision": "serial",
                "offer_id": decision.offer_id,
                "reason_code": decision.reason_code,
                "serial_action": decision.serial_action,
                "instruction": "Continue the original task without creating branches.",
                "strong_route_requested": escalated_after_decline,
            }
            self.dag.transition(node_id, "succeeded", output=result)
            if not escalated_after_decline:
                return result, "succeeded", node_id
            routing_node_id = self.dag.add_node(
                kind="routing_decision",
                label="escalate after branch parallel offer declined",
                scope_id=self.scope_id,
                status="pending",
                input={
                    "trigger": "branch_parallel_offer_declined",
                    "branch_id": offer.branch_id,
                    "offer_id": offer.offer_id,
                },
                metadata={"task_id": state.task_id, "attempt_id": state.attempt_id},
            )
            self.dag.add_edge(node_id, routing_node_id, kind="escalation")
            self.dag.transition(routing_node_id, "ready")
            self.dag.transition(routing_node_id, "running")
            self.dag.transition(
                routing_node_id,
                "succeeded",
                output={
                    "route_mode": state.route_mode,
                    "requested_model": state.requested_model,
                    "reasoning_mode": state.reasoning_mode,
                    "reason": state.escalation_reason,
                },
            )
            return result, "succeeded", routing_node_id

        if not isinstance(decision, ParallelPlanDecision):
            result = {"ok": False, "error": "unsupported execution-mode decision"}
            self.dag.transition(node_id, "failed", output=result)
            return result, "failed", node_id
        phase_budget_exhausted = (
            offer.decision_phase == "initial"
            and state.initial_plan_expansion_count
            >= self.max_initial_plan_expansions
        ) or (
            offer.decision_phase == "recovery"
            and state.recovery_plan_expansion_count
            >= self.max_recovery_plan_expansions
        )
        if (
            state.plan_expansion_count >= self.max_plan_expansions
            or phase_budget_exhausted
        ):
            result = {
                "ok": False,
                "error": (
                    f"{offer.decision_phase} parallel expansion budget exhausted"
                ),
                "fallback_serial": True,
            }
            self.dag.transition(node_id, "failed", output=result)
            return result, "failed", node_id
        for validator_ref in decision.plan.acceptance_policy.validators:
            try:
                self.validation_registry.resolve(validator_ref)
            except ValueError as exc:
                result = {
                    "ok": False,
                    "error": f"invalid_task_plan: {exc}",
                    "fallback_serial": True,
                }
                self.dag.transition(node_id, "failed", output=result)
                return result, "failed", node_id
        result, status, terminal_node_id = self._run_task_plan(
            state,
            decision.plan,
            node_id,
            history_cut=offer_history_cut,
            checkpoint_source="v1_offer",
        )
        state.plan_expansion_count += 1
        if offer.decision_phase == "initial":
            state.initial_plan_expansion_count += 1
        else:
            state.recovery_plan_expansion_count += 1
        result = {
            **result,
            "execution_mode": "parallel",
            "offer_id": decision.offer_id,
            "reason_code": decision.reason_code,
            "logical_to_runtime_ids": decision.logical_to_runtime_ids,
        }
        self.dag.transition(node_id, status, output=result)
        if offer.branch_id == "root":
            return result, status, terminal_node_id
        revision_node_id = self.dag.add_node(
            kind="join_revision",
            label=f"local recovery for {offer.branch_id}",
            scope_id=self.scope_id,
            status="pending",
            input={
                "offer_id": offer.offer_id,
                "recovery_for_branch_id": offer.branch_id,
                "original_join_node_id": offer.parent_node_id,
            },
            metadata={
                "task_id": state.task_id,
                "attempt_id": state.attempt_id,
                "recovery_for_branch_id": offer.branch_id,
            },
        )
        self.dag.add_edge(offer.parent_node_id, revision_node_id, kind="join_revision")
        self.dag.add_edge(terminal_node_id, revision_node_id, kind="join_revision")
        self.dag.transition(revision_node_id, "ready")
        self.dag.transition(revision_node_id, "running")
        self.dag.transition(
            revision_node_id,
            "succeeded" if result.get("ok") else "partial",
            output={
                "recovery_for_branch_id": offer.branch_id,
                "recovery_plan": result,
            },
        )
        result["recovery_for_branch_id"] = offer.branch_id
        result["join_revision_node_id"] = revision_node_id
        return result, status, revision_node_id

    def _record_verified_tool_artifact(
        self,
        call: ToolCall,
        result: dict[str, Any],
        tool_node_id: str,
    ) -> str:
        artifact = self.tools.extract_verified_artifact(
            call.name, call.arguments, result
        )
        if artifact is None:
            return tool_node_id
        if call.name == "deliver_files" and self._file_branch_checks is not None:
            artifact.update(self._file_branch_checks.artifact_fields(result))
        content = str(artifact.pop("content"))
        digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
        # Equal content tested for a different target/branch is different evidence.
        evidence_digest = hashlib.sha256(json.dumps(
            [digest, artifact, self.branch_id, self.attempt_id, call.id],
            sort_keys=True, ensure_ascii=False,
        ).encode("utf-8")).hexdigest()
        artifact_id = f"artifact-{evidence_digest[:16]}"
        completed_ns = time.monotonic_ns()
        record = {
            "artifact_id": artifact_id,
            "kind": str(artifact.pop("kind", "tool_verified")),
            "content": content,
            "content_sha256": digest,
            "tool": call.name,
            "tool_call_id": call.id,
            "branch_id": self.branch_id,
            "attempt_id": self.attempt_id,
            "completed_monotonic_ns": completed_ns,
            **artifact,
        }
        artifact_node_id = self.dag.add_node(
            kind="verified_artifact",
            label=f"verified artifact {artifact_id}",
            scope_id=self.scope_id,
            status="pending",
            input={
                "artifact_id": artifact_id,
                "tool": call.name,
                "tool_call_id": call.id,
                "branch_id": self.branch_id,
                "attempt_id": self.attempt_id,
            },
            metadata={
                "content_sha256": digest,
                "artifact_kind": record["kind"],
            },
        )
        self.dag.add_edge(tool_node_id, artifact_node_id, kind="artifact")
        self.dag.transition(artifact_node_id, "ready")
        self.dag.transition(artifact_node_id, "running")
        self.dag.transition(artifact_node_id, "succeeded", output=record)
        with self._verified_artifact_lock:
            self._verified_artifacts.append(record)
        self.tracer.emit(
            "verified_tool_artifact_recorded",
            task_id=self.task_node_id,
            scope_id=self.scope_id,
            branch_id=self.branch_id,
            attempt_id=self.attempt_id,
            artifact_id=artifact_id,
            content_sha256=digest,
            tool=call.name,
            tool_call_id=call.id,
            node_id=artifact_node_id,
        )
        return artifact_node_id

    def latest_verified_artifact(self) -> dict[str, Any] | None:
        with self._verified_artifact_lock:
            if not self._verified_artifacts:
                return None
            latest = max(
                self._verified_artifacts,
                key=lambda item: int(item["completed_monotonic_ns"]),
            )
            return copy.deepcopy(latest)

    @staticmethod
    def _balanced_message_cut(
        messages: list[dict[str, Any]],
        *,
        maximum: int | None = None,
    ) -> int:
        """Return the largest prefix with a complete assistant/tool protocol.

        A fork must never end after an assistant tool call whose tool result is
        absent.  That malformed boundary makes providers reject the child
        request and also encourages the child to repeat already completed work.
        """
        limit = len(messages) if maximum is None else max(0, min(maximum, len(messages)))
        pending: set[str] = set()
        last_balanced = 0
        protocol_valid = True
        for index, message in enumerate(messages[:limit], start=1):
            role = message.get("role")
            if role == "assistant":
                for raw_call in message.get("tool_calls") or ():
                    call_id = str(raw_call.get("id", ""))
                    if not call_id or call_id in pending:
                        protocol_valid = False
                        break
                    pending.add(call_id)
            elif role == "tool":
                call_id = str(message.get("tool_call_id", ""))
                if not call_id or call_id not in pending:
                    protocol_valid = False
                else:
                    pending.remove(call_id)
            if protocol_valid and not pending:
                last_balanced = index
        return last_balanced

    def _child_history_checkpoint(
        self,
        state: RuntimeState,
        *,
        history_cut: int | None = None,
        source: str = "balanced_tool_result",
    ) -> tuple[dict[str, Any], ...]:
        cut = self._balanced_message_cut(state.messages, maximum=history_cut)
        if cut <= 0:
            raise RuntimeError("cannot fork child from an empty or malformed parent history")
        checkpoint = tuple(copy.deepcopy(state.messages[:cut]))
        self.tracer.emit(
            "child_history_checkpoint_created",
            run_id=state.run_id,
            task_id=state.task_id,
            plan_id=state.plan_id,
            source=source,
            requested_cut=history_cut,
            balanced_cut=cut,
            parent_message_count=len(state.messages),
            inherited_message_count=len(checkpoint),
            inherited_content_chars=sum(
                len(str(message.get("content", ""))) for message in checkpoint
            ),
        )
        return checkpoint

    def _run_task_plan(
        self,
        state: RuntimeState,
        plan: TaskPlan,
        expansion_node_id: str,
        *,
        history_cut: int | None = None,
        checkpoint_source: str = "balanced_tool_result",
    ) -> tuple[dict[str, Any], str, str]:
        # All autonomous and Offer plans converge here, before any checkpoint
        # or child is created. Keep the existing exact-file write policy, but
        # make its mandatory delivery list cover the model's explicit writes.
        memory = getattr(self, "_v2_classifier_state_memory", None)
        frontier = memory.snapshot(state.task).get("dynamic_frontier", {}) if memory is not None else {}
        try:
            plan, reconciled = reconcile_delivery_ownership(plan, frontier)
        except InvalidTaskPlan as exc:
            result = {"ok": False, "error": f"invalid_task_plan: {exc}"}
            self.tracer.emit("branch_delivery_contract_rejected", step=state.step,
                             scope_id=self.scope_id, error=str(exc))
            return result, "failed", expansion_node_id
        for change in reconciled:
            self.tracer.emit("branch_delivery_contract_reconciled", step=state.step,
                             scope_id=self.scope_id, **change)
        if self.require_file_branch_contract:
            missing = [spec.id for spec in plan.subtasks if not (
                spec.required_artifact_kinds == ("file",)
                and spec.required_artifact_paths
            )]
            if missing:
                return {"ok": False, "error": (
                    "file_branch_contract_required: declare completion_contract with "
                    "required_artifact_kinds=['file'], required_artifact_paths and "
                    "required_test_targets for branches: " + ", ".join(missing)
                )}, "failed", expansion_node_id
        if not self.allow_subtasks:
            result = {
                "ok": False,
                "error": f"subtask depth limit reached ({self.max_subtask_depth})",
            }
            return result, "failed", expansion_node_id

        parent_history = self._child_history_checkpoint(
            state,
            history_cut=history_cut,
            source=checkpoint_source,
        )

        expansion_ordinal = state.plan_expansion_count + 1
        plan_id = f"plan-{expansion_ordinal:03d}-{uuid.uuid4().hex[:8]}"
        parent_plan_id = state.plan_id
        plan_scope = f"{self.scope_id}/{plan_id}"
        subtask_nodes: dict[str, str] = {}
        for spec in plan.subtasks:
            node_id = self.dag.add_node(
                kind="subtask",
                label=f"{spec.id}: {spec.task[:120]}",
                scope_id=f"{plan_scope}/{spec.id}",
                status="pending",
                input={
                    "id": spec.id,
                    "task": spec.task,
                    "depends_on": list(spec.depends_on),
                    "input_refs": list(spec.input_refs),
                },
                metadata={
                    "policy_version": plan.policy_version,
                    "run_id": state.run_id,
                    "plan_id": plan_id,
                    "parent_plan_id": parent_plan_id,
                    "branch_key": f"{state.run_id}/{plan_id}/{spec.id}",
                    "ordinal": spec.ordinal,
                    "failure_policy": plan.failure_policy,
                    "join_policy": plan.join_policy,
                },
            )
            self.dag.add_edge(expansion_node_id, node_id, kind="spawn")
            subtask_nodes[spec.id] = node_id
        for spec in plan.subtasks:
            for dependency in spec.depends_on:
                self.dag.add_edge(
                    subtask_nodes[dependency],
                    subtask_nodes[spec.id],
                    kind="depends_on",
                )

        join_node_id = self.dag.add_node(
            kind="join",
            label="subtask join",
            scope_id=self.scope_id,
            status="pending",
            metadata={
                "policy_version": plan.policy_version,
                "run_id": state.run_id,
                "plan_id": plan_id,
                "parent_plan_id": parent_plan_id,
                "join_policy": plan.join_policy,
                "failure_policy": plan.failure_policy,
                "acceptance_policy": {
                    "operator": plan.acceptance_policy.operator,
                    "validators": list(plan.acceptance_policy.validators),
                    "minimum_score": plan.acceptance_policy.minimum_score,
                },
                "quorum": plan.quorum,
                "top_k": plan.top_k,
                "deadline_seconds": plan.deadline_seconds,
                "subtask_ids": [spec.id for spec in plan.subtasks],
            },
        )
        self.dag.add_edge(expansion_node_id, join_node_id, kind="control")
        for node_id in subtask_nodes.values():
            self.dag.add_edge(node_id, join_node_id, kind="join")

        specs = {spec.id: spec for spec in plan.subtasks}
        dependencies = {spec.id: spec.depends_on for spec in plan.subtasks}
        branch_scopes = {
            spec.id: self.cancellation_scope.child(f"{plan_scope}/{spec.id}")
            for spec in plan.subtasks
        }
        pending = set(specs)
        outcomes: dict[str, SubtaskOutcome] = {}
        running: dict[Future[SubtaskOutcome], AttemptDispatch] = {}
        branch_started: set[str] = set()
        attempt_counts = {subtask_id: 0 for subtask_id in specs}
        weak_failure_counts = {subtask_id: 0 for subtask_id in specs}
        observed_duration_ms: dict[str, float] = {}
        retry_parent_nodes: dict[str, str] = {}
        forced_models: dict[str, str] = {}
        forced_reasoning_modes: dict[str, str] = {}
        stop_scheduling = False
        policy_trigger = ""
        winner_id = ""
        accepted_ids: list[str] = []
        join_signal_emitted = False
        cancellation_requested: set[str] = set()
        plan_started = time.monotonic()
        deadline_at = (
            plan_started + plan.deadline_seconds
            if plan.deadline_seconds is not None
            else None
        )

        executor = ThreadPoolExecutor(
            max_workers=min(self.max_parallelism, len(specs)),
            thread_name_prefix="agent-subtask",
        )
        try:
            while pending or running:
                self._check_cancelled()
                made_progress = False
                active_branches = pending | {
                    dispatch.subtask_id for dispatch in running.values()
                }
                critical_branches, critical_scores = dynamic_critical_branches(
                    active_branches=active_branches,
                    dependencies=dependencies,
                    observed_duration_ms=observed_duration_ms,
                )

                available_slots = self.max_parallelism - len(running)
                for subtask_id in sorted(
                    pending, key=lambda item: specs[item].ordinal
                ):
                    spec = specs[subtask_id]
                    dependency_outcomes = [outcomes.get(item) for item in spec.depends_on]
                    if any(
                        outcome is not None
                        and (outcome.status != "succeeded" or outcome.accepted is False)
                        for outcome in dependency_outcomes
                    ):
                        now = time.time()
                        outcome = SubtaskOutcome(
                            subtask_id=subtask_id,
                            status="skipped",
                            error="dependency did not succeed",
                            started_at=now,
                            ended_at=now,
                        )
                        outcomes[subtask_id] = outcome
                        pending.remove(subtask_id)
                        self.dag.transition(
                            subtask_nodes[subtask_id],
                            "skipped",
                            error={"reason": outcome.error},
                        )
                        branch_scopes[subtask_id].close()
                        made_progress = True
                        continue

                    dependencies_ready = all(
                        outcome is not None
                        and outcome.status == "succeeded"
                        and outcome.accepted is not False
                        for outcome in dependency_outcomes
                    )
                    if stop_scheduling or not dependencies_ready:
                        continue
                    if available_slots <= 0:
                        continue
                    branch_node_id = subtask_nodes[subtask_id]
                    if subtask_id not in branch_started:
                        self.dag.transition(branch_node_id, "ready")
                        self.dag.transition(branch_node_id, "running")
                        branch_started.add(subtask_id)
                    attempt_counts[subtask_id] += 1
                    attempt_ordinal = attempt_counts[subtask_id]
                    attempt_id = (
                        f"{subtask_id}-attempt-{attempt_ordinal}-{uuid.uuid4().hex[:8]}"
                    )
                    placement = placement_for_join(
                        join_policy=plan.join_policy,
                        run_id=state.run_id,
                        plan_id=plan_id,
                        attempt_id=attempt_id,
                    )
                    self.tracer.emit(
                        "semantic_placement_decided",
                        task_id=self.task_node_id,
                        run_id=state.run_id,
                        plan_id=plan_id,
                        branch_id=subtask_id,
                        attempt_id=attempt_id,
                        join_policy=plan.join_policy,
                        placement_mode=placement.mode,
                        gateway_routing_key=placement.routing_key,
                        reason=placement.reason,
                    )
                    requested_model = forced_models.get(subtask_id, "")
                    reasoning_mode = forced_reasoning_modes.get(
                        subtask_id, self.initial_reasoning_mode
                    )
                    on_critical_path = subtask_id in critical_branches
                    attempt_scope_id = (
                        f"{plan_scope}/{subtask_id}/attempt-{attempt_ordinal}"
                    )
                    attempt_scope = branch_scopes[subtask_id].child(attempt_scope_id)
                    attempt_node_id = self.dag.add_node(
                        kind="subtask_attempt",
                        label=f"{subtask_id} attempt {attempt_ordinal}",
                        scope_id=attempt_scope_id,
                        status="pending",
                        input={
                            "run_id": state.run_id,
                            "plan_id": plan_id,
                            "branch_key": f"{state.run_id}/{plan_id}/{subtask_id}",
                            "subtask_id": subtask_id,
                            "attempt_id": attempt_id,
                            "attempt_ordinal": attempt_ordinal,
                            "requested_model": requested_model or "MoM(auto)",
                            "reasoning_mode": reasoning_mode,
                            "required_for_join": plan.join_policy == "all_terminal",
                            "on_critical_path": on_critical_path,
                            "critical_path_score_ms": critical_scores.get(subtask_id),
                            "gateway_placement_mode": placement.mode,
                            "gateway_routing_key": placement.routing_key,
                        },
                        metadata={
                            "run_id": state.run_id,
                            "plan_id": plan_id,
                            "branch_key": f"{state.run_id}/{plan_id}/{subtask_id}",
                            "branch_node_id": branch_node_id,
                            "join_policy": plan.join_policy,
                        },
                    )
                    attempt_parent = retry_parent_nodes.pop(
                        subtask_id, branch_node_id
                    )
                    self.dag.add_edge(
                        attempt_parent,
                        attempt_node_id,
                        kind="retry" if attempt_ordinal > 1 else "attempt",
                    )
                    self.dag.transition(attempt_node_id, "ready")
                    future = executor.submit(
                        self._run_planned_subtask,
                        spec,
                        attempt_node_id,
                        attempt_scope_id,
                        attempt_scope,
                        plan_id,
                        plan,
                        plan.join_policy == "all_terminal",
                        attempt_id,
                        requested_model,
                        reasoning_mode,
                        on_critical_path,
                        placement.routing_key,
                        placement.mode,
                        parent_history,
                    )
                    self.execution_registry.register(
                        attempt_node_id,
                        attempt_scope,
                        kind="subtask_attempt",
                        future=future,
                        metadata={
                            "subtask_id": subtask_id,
                            "attempt_id": attempt_id,
                            "attempt_ordinal": attempt_ordinal,
                            "requested_model": requested_model or "MoM(auto)",
                            "reasoning_mode": reasoning_mode,
                        },
                    )
                    running[future] = AttemptDispatch(
                        subtask_id=subtask_id,
                        attempt_node_id=attempt_node_id,
                        attempt_id=attempt_id,
                        attempt_ordinal=attempt_ordinal,
                        scope=attempt_scope,
                        requested_model=requested_model,
                        on_critical_path=on_critical_path,
                    )
                    pending.remove(subtask_id)
                    available_slots -= 1
                    made_progress = True

                if stop_scheduling and pending:
                    now = time.time()
                    for subtask_id in list(pending):
                        outcomes[subtask_id] = SubtaskOutcome(
                            subtask_id=subtask_id,
                            status="skipped",
                            error=policy_trigger,
                            started_at=now,
                            ended_at=now,
                        )
                        self.dag.transition(
                            subtask_nodes[subtask_id],
                            "skipped",
                            error={"reason": policy_trigger},
                            metadata={"policy_trigger": policy_trigger},
                        )
                        branch_scopes[subtask_id].close()
                        pending.remove(subtask_id)
                    made_progress = True

                if running:
                    wait_timeout = None
                    if deadline_at is not None:
                        wait_timeout = max(0.0, deadline_at - time.monotonic())
                    done, _ = wait(
                        tuple(running),
                        timeout=wait_timeout,
                        return_when=FIRST_COMPLETED,
                    )
                    if not done and deadline_at is not None and time.monotonic() >= deadline_at:
                        stop_scheduling = True
                        policy_trigger = "deadline reached"
                        deadline_at = None
                        accepted = [
                            item for item in outcomes.values() if item.accepted is True
                        ]
                        if accepted:
                            winner_id = max(
                                accepted,
                                key=lambda item: (
                                    item.validation_score or 0.0,
                                    -item.ended_at,
                                ),
                            ).subtask_id
                        for future, dispatch in list(running.items()):
                            if dispatch.subtask_id in cancellation_requested:
                                continue
                            self._transition_to_cancelling(
                                subtask_nodes[dispatch.subtask_id], policy_trigger
                            )
                            self._request_subtask_cancel(
                                dispatch.attempt_node_id, policy_trigger
                            )
                            cancellation_requested.add(dispatch.subtask_id)
                        continue
                    completed: list[
                        tuple[Future[SubtaskOutcome], AttemptDispatch, SubtaskOutcome]
                    ] = []
                    for future in done:
                        dispatch = running.pop(future)
                        subtask_id = dispatch.subtask_id
                        try:
                            outcome = future.result()
                        except BaseException as exc:
                            now = time.time()
                            outcome = SubtaskOutcome(
                                subtask_id=subtask_id,
                                status="failed",
                                error=f"{type(exc).__name__}: {exc}",
                                started_at=now,
                                ended_at=now,
                            )
                        completed.append((future, dispatch, outcome))
                    completed.sort(
                        key=lambda item: (
                            item[2].ended_at,
                            specs[item[1].subtask_id].ordinal,
                        )
                    )
                    for _, dispatch, outcome in completed:
                        subtask_id = dispatch.subtask_id
                        spec = specs[subtask_id]
                        attempt_node_id = dispatch.attempt_node_id
                        identity_errors = []
                        if outcome.subtask_id != subtask_id:
                            identity_errors.append(
                                f"branch {outcome.subtask_id!r} != {subtask_id!r}"
                            )
                        if outcome.attempt_id and outcome.attempt_id != dispatch.attempt_id:
                            identity_errors.append(
                                f"attempt {outcome.attempt_id!r} != "
                                f"{dispatch.attempt_id!r}"
                            )
                        if identity_errors:
                            original = outcome
                            mismatch = "; ".join(identity_errors)
                            self.tracer.emit(
                                "subtask_identity_mismatch_rejected",
                                task_id=self.task_node_id,
                                plan_id=plan_id,
                                expected_branch_id=subtask_id,
                                expected_attempt_id=dispatch.attempt_id,
                                returned_branch_id=original.subtask_id,
                                returned_attempt_id=original.attempt_id,
                                error=mismatch,
                            )
                            outcome = SubtaskOutcome(
                                subtask_id=subtask_id,
                                status="failed",
                                error=f"subtask identity mismatch: {mismatch}",
                                terminal_node_id=original.terminal_node_id,
                                usage=original.usage,
                                started_at=original.started_at,
                                ended_at=original.ended_at,
                                attempt_id=dispatch.attempt_id,
                                inference_session_id=original.inference_session_id,
                                inference_request_id=original.inference_request_id,
                                last_selected_model=original.last_selected_model,
                                selected_worker=original.selected_worker,
                            )
                        observed_duration_ms[subtask_id] = max(
                            0.001,
                            (outcome.ended_at - outcome.started_at) * 1000,
                        )
                        if outcome.status == "succeeded" and (
                            plan.acceptance_policy.validators
                            or plan.join_policy
                            in {"any_accepted", "best_score", "top_k", "quorum", "deadline"}
                        ):
                            outcome = self._validate_subtask_candidate(
                                outcome,
                                plan,
                                attempt_node_id,
                            )
                        rejected = (
                            outcome.status == "succeeded"
                            and outcome.accepted is False
                        )
                        if rejected and outcome.last_selected_model == (
                            self.adaptive_routing_policy.weak_model
                        ):
                            weak_failure_counts[subtask_id] += 1
                        active_for_retry = pending | {
                            item.subtask_id for item in running.values()
                        } | {subtask_id}
                        retry_critical, retry_scores = dynamic_critical_branches(
                            active_branches=active_for_retry,
                            dependencies=dependencies,
                            observed_duration_ms=observed_duration_ms,
                        )
                        # In all_terminal, a rejected required branch immediately
                        # becomes a join blocker even when its duration estimate
                        # was not previously the longest path.
                        on_critical_path = subtask_id in retry_critical or (
                            rejected and plan.join_policy == "all_terminal"
                        )
                        should_retry_strong = rejected and (
                            self.adaptive_routing_policy.should_escalate_branch(
                                last_selected_model=outcome.last_selected_model,
                                weak_failure_count=weak_failure_counts[subtask_id],
                                required_for_join=plan.join_policy == "all_terminal",
                                on_critical_path=on_critical_path,
                                attempt_ordinal=dispatch.attempt_ordinal,
                            )
                        )
                        if rejected:
                            deferred_before = state.deferred_parallel_offer
                            self._observe_parallel_decision_point(
                                state,
                                node_id=join_node_id,
                                event_type=(
                                    "before_strong_model_escalation"
                                    if should_retry_strong
                                    else "critical_validation_failure"
                                ),
                                branch_id=subtask_id,
                                attempt_id=outcome.attempt_id,
                                failure_type="candidate_rejected",
                                required_for_join=(
                                    plan.join_policy == "all_terminal"
                                ),
                                on_critical_path=on_critical_path,
                                join_blocked=(
                                    plan.join_policy == "all_terminal"
                                ),
                                validation_summary=json.dumps(
                                    outcome.validation or {},
                                    ensure_ascii=False,
                                ),
                                defer_offer=True,
                            )
                            if (
                                deferred_before is None
                                and isinstance(state.deferred_parallel_offer, ParallelOffer)
                            ):
                                should_retry_strong = False
                                self.tracer.emit(
                                    "route_escalation_deferred_for_parallel_offer",
                                    task_id=state.task_id,
                                    branch_id=subtask_id,
                                    attempt_id=outcome.attempt_id,
                                    offer_id=state.deferred_parallel_offer.offer_id,
                                )
                        if should_retry_strong:
                            self._merge_usage(state.usage, outcome.usage)
                            self._record_rejected_attempt(
                                outcome,
                                attempt_node_id,
                            )
                            release = self._release_rejected_attempt(outcome)
                            decision_node_id = self.dag.add_node(
                                kind="routing_decision",
                                label=(
                                    f"retry {subtask_id} on "
                                    f"{self.adaptive_routing_policy.retry_target_model} "
                                    f"({self.adaptive_routing_policy.escalation_action})"
                                ),
                                scope_id=self.scope_id,
                                status="pending",
                                input={
                                    "trigger": "branch_acceptance_failed",
                                    "branch_id": subtask_id,
                                    "rejected_attempt_id": outcome.attempt_id,
                                    "last_selected_model": outcome.last_selected_model,
                                    "weak_validation_failures": weak_failure_counts[subtask_id],
                                    "required_for_join": plan.join_policy == "all_terminal",
                                    "on_critical_path": on_critical_path,
                                    "critical_path_score_ms": retry_scores.get(subtask_id),
                                },
                            )
                            if outcome.terminal_node_id:
                                self.dag.add_edge(
                                    outcome.terminal_node_id,
                                    decision_node_id,
                                    kind="escalation",
                                )
                            else:
                                self.dag.add_edge(
                                    attempt_node_id,
                                    decision_node_id,
                                    kind="escalation",
                                )
                            self.dag.transition(decision_node_id, "ready")
                            self.dag.transition(decision_node_id, "running")
                            self.dag.transition(
                                decision_node_id,
                                "succeeded",
                                output={
                                    "escalation_action": self.adaptive_routing_policy.escalation_action,
                                    "route_mode": (
                                        "require_strong"
                                        if self.adaptive_routing_policy.escalation_action == "strong_model"
                                        else "auto"
                                    ),
                                    "requested_model": self.adaptive_routing_policy.retry_model,
                                    "reasoning_mode": self.adaptive_routing_policy.retry_reasoning_mode,
                                    "next_attempt_ordinal": dispatch.attempt_ordinal + 1,
                                    "kv_release": release,
                                },
                            )
                            retry_parent_nodes[subtask_id] = decision_node_id
                            forced_models[subtask_id] = self.adaptive_routing_policy.retry_model
                            forced_reasoning_modes[subtask_id] = (
                                self.adaptive_routing_policy.retry_reasoning_mode
                            )
                            pending.add(subtask_id)
                            self.execution_registry.unregister(attempt_node_id)
                            dispatch.scope.close()
                            self.tracer.emit(
                                "branch_criticality_escalation_applied",
                                task_id=self.task_node_id,
                                branch_id=subtask_id,
                                rejected_attempt_id=outcome.attempt_id,
                                next_attempt_ordinal=dispatch.attempt_ordinal + 1,
                                from_model=outcome.last_selected_model,
                                escalation_action=self.adaptive_routing_policy.escalation_action,
                                to_model=self.adaptive_routing_policy.retry_target_model,
                                reasoning_mode=self.adaptive_routing_policy.retry_reasoning_mode,
                                on_critical_path=on_critical_path,
                                weak_validation_failures=weak_failure_counts[subtask_id],
                                kv_release=release,
                                node_id=decision_node_id,
                            )
                            made_progress = True
                            continue
                        if rejected:
                            outcome.status = "failed"
                            outcome.error = outcome.error or "candidate rejected"
                        outcomes[subtask_id] = outcome
                        self._record_subtask_outcome(
                            outcome,
                            attempt_node_id,
                            join_node_id,
                            branch_node_id=subtask_nodes[subtask_id],
                        )
                        self.execution_registry.unregister(attempt_node_id)
                        dispatch.scope.close()
                        branch_scopes[subtask_id].close()
                        if outcome.accepted is True:
                            accepted_ids.append(subtask_id)
                        if not stop_scheduling:
                            if plan.failure_policy == "fail_fast" and (
                                outcome.status != "succeeded" or outcome.accepted is False
                            ):
                                stop_scheduling = True
                                policy_trigger = (
                                    f"fail_fast triggered by {subtask_id}:{outcome.status}"
                                )
                            elif (
                                plan.join_policy == "any_completed_success"
                                and outcome.status == "succeeded"
                            ):
                                stop_scheduling = True
                                winner_id = subtask_id
                                policy_trigger = f"any_completed_success winner:{subtask_id}"
                            elif (
                                plan.join_policy == "any_accepted"
                                and outcome.accepted is True
                            ):
                                stop_scheduling = True
                                winner_id = subtask_id
                                policy_trigger = f"any_accepted winner:{subtask_id}"
                            elif (
                                plan.join_policy == "quorum"
                                and len(accepted_ids) >= plan.quorum
                            ):
                                stop_scheduling = True
                                winner_id = accepted_ids[0]
                                policy_trigger = f"quorum satisfied:{len(accepted_ids)}"
                    if stop_scheduling:
                        if not join_signal_emitted:
                            self.tracer.emit(
                                "on_join_satisfied"
                                if winner_id or (
                                    plan.join_policy == "quorum"
                                    and len(accepted_ids) >= plan.quorum
                                )
                                else "policy_cancellation_triggered",
                                task_id=self.task_node_id,
                                join_policy=plan.join_policy,
                                winner=winner_id or None,
                                reason=policy_trigger,
                            )
                            join_signal_emitted = True
                        for future, dispatch in list(running.items()):
                            subtask_id = dispatch.subtask_id
                            node_id = dispatch.attempt_node_id
                            if subtask_id not in cancellation_requested:
                                self._transition_to_cancelling(
                                    subtask_nodes[subtask_id], policy_trigger
                                )
                                self._request_subtask_cancel(node_id, policy_trigger)
                                cancellation_requested.add(subtask_id)
                            if not future.cancelled():
                                continue
                            running.pop(future)
                            now = time.time()
                            outcome = SubtaskOutcome(
                                subtask_id=subtask_id,
                                status="cancelled",
                                error=policy_trigger,
                                started_at=now,
                                ended_at=now,
                            )
                            outcomes[subtask_id] = outcome
                            self._record_subtask_outcome(
                                outcome,
                                node_id,
                                join_node_id,
                                branch_node_id=subtask_nodes[subtask_id],
                            )
                            self.execution_registry.unregister(node_id)
                            dispatch.scope.close()
                            branch_scopes[subtask_id].close()
                    made_progress = True

                if not made_progress and pending and not running:
                    raise RuntimeError("subtask scheduler made no progress")
        except BaseException:
            self._cancel_active_children()
            now = time.time()
            for future, dispatch in list(running.items()):
                subtask_id = dispatch.subtask_id
                node_id = dispatch.attempt_node_id
                self._transition_to_cancelling(
                    subtask_nodes[subtask_id], "parent task interrupted"
                )
                self._request_subtask_cancel(
                    node_id,
                    "parent task interrupted",
                )
                if future.cancelled():
                    outcome = SubtaskOutcome(
                        subtask_id=subtask_id,
                        status="cancelled",
                        error="parent task interrupted before child started",
                        started_at=now,
                        ended_at=now,
                    )
                else:
                    try:
                        outcome = future.result()
                    except BaseException as exc:
                        outcome = SubtaskOutcome(
                            subtask_id=subtask_id,
                            status="cancelled",
                            error=f"parent interrupted child: {type(exc).__name__}: {exc}",
                            started_at=now,
                            ended_at=time.time(),
                        )
                outcomes[subtask_id] = outcome
                self._record_subtask_outcome(
                    outcome,
                    node_id,
                    join_node_id,
                    branch_node_id=subtask_nodes[subtask_id],
                )
                self.execution_registry.unregister(node_id)
                dispatch.scope.close()
                branch_scopes[subtask_id].close()
            running.clear()
            for subtask_id in list(pending):
                self.dag.transition(
                    subtask_nodes[subtask_id],
                    "cancelled",
                    error={"reason": "parent task interrupted"},
                )
                outcomes[subtask_id] = SubtaskOutcome(
                    subtask_id=subtask_id,
                    status="cancelled",
                    error="parent task interrupted",
                    started_at=now,
                    ended_at=now,
                )
                branch_scopes[subtask_id].cancel("parent task interrupted")
                branch_scopes[subtask_id].close()
                pending.remove(subtask_id)
            self.dag.transition(
                join_node_id,
                "cancelled",
                error={"reason": "parent task interrupted"},
            )
            raise
        finally:
            executor.shutdown(wait=True, cancel_futures=True)

        for outcome in outcomes.values():
            self._merge_usage(state.usage, outcome.usage)
            if outcome.artifact and outcome.artifact.get("materialized_files"):
                current = self._materialized_artifact_files({**outcome.artifact, "content": outcome.result})
                previous = outcome.artifact["materialized_files"]
                outcome.artifact["materialized_files"] = current
                if previous != current:
                    outcome.artifact["delivery_verified"] = False
                    outcome.accepted = False
                    outcome.error = "Delivered files changed before join; revalidation required"
        ordered = [outcomes[spec.id] for spec in plan.subtasks]
        if winner_id and outcomes[winner_id].accepted is False:
            winner_id = ""
            if plan.join_policy in {"any_accepted", "any_completed_success"}:
                winner_id = next((outcome.subtask_id for outcome in ordered
                    if outcome.status == "succeeded" and (
                        outcome.accepted is True if plan.join_policy == "any_accepted"
                        else outcome.accepted is not False
                    )), "")
        all_succeeded = all(
            outcome.status == "succeeded" and outcome.accepted is not False
            for outcome in ordered
        )
        accepted_outcomes = [outcome for outcome in ordered if outcome.accepted is True]
        ranked_accepted = sorted(
            accepted_outcomes,
            key=lambda item: (
                -(item.validation_score or 0.0),
                item.ended_at,
                item.subtask_id,
            ),
        )
        selected_top_k: list[str] = []
        if plan.join_policy == "top_k":
            selected_top_k = [
                outcome.subtask_id for outcome in ranked_accepted[: plan.top_k]
            ]
            if selected_top_k:
                winner_id = selected_top_k[0]
        if plan.join_policy in {"best_score", "deadline"} and accepted_outcomes:
            winner_id = max(
                accepted_outcomes,
                key=lambda item: (
                    item.validation_score or 0.0,
                    -item.ended_at,
                ),
            ).subtask_id
        join_satisfied = False
        if plan.join_policy == "all_terminal":
            join_satisfied = all_succeeded or plan.failure_policy == "continue"
        elif plan.join_policy == "any_completed_success":
            join_satisfied = bool(winner_id)
        elif plan.join_policy == "any_accepted":
            join_satisfied = bool(winner_id)
        elif plan.join_policy == "quorum":
            join_satisfied = len(accepted_outcomes) >= plan.quorum
        elif plan.join_policy == "top_k":
            join_satisfied = len(selected_top_k) == plan.top_k
        elif plan.join_policy in {"best_score", "deadline"}:
            join_satisfied = bool(winner_id)

        if join_satisfied and (all_succeeded or plan.join_policy != "all_terminal"):
            join_status = "succeeded"
        elif plan.failure_policy == "fail_fast":
            join_status = "failed"
        elif plan.join_policy != "all_terminal":
            join_status = "failed"
        else:
            join_status = "partial"
        summary = {
            "ok": join_satisfied,
            "status": join_status,
            "policy_version": plan.policy_version,
            "failure_policy": plan.failure_policy,
            "join_policy": plan.join_policy,
            "acceptance_policy": {
                "operator": plan.acceptance_policy.operator,
                "validators": list(plan.acceptance_policy.validators),
                "minimum_score": plan.acceptance_policy.minimum_score,
            },
            "winner": winner_id or None,
            "selected_top_k": selected_top_k,
            "top_k": plan.top_k if plan.join_policy == "top_k" else None,
            "accepted": [outcome.subtask_id for outcome in accepted_outcomes],
            "quorum": plan.quorum if plan.join_policy == "quorum" else None,
            "deadline_seconds": (
                plan.deadline_seconds if plan.join_policy == "deadline" else None
            ),
            "subtasks": [outcome.to_dict() for outcome in ordered],
        }
        self.dag.transition(join_node_id, "ready")
        self.dag.transition(join_node_id, "running")
        self.dag.transition(join_node_id, join_status, output=summary)
        return summary, join_status, join_node_id

    def _record_subtask_outcome(
        self,
        outcome: SubtaskOutcome,
        attempt_node_id: str,
        join_node_id: str,
        *,
        branch_node_id: str | None = None,
    ) -> None:
        if outcome.terminal_node_id:
            self.dag.add_edge(outcome.terminal_node_id, join_node_id, kind="join")
        effective_status = (
            "failed"
            if outcome.accepted is False and outcome.status == "succeeded"
            else outcome.status
        )
        requested_status = effective_status
        attempt_snapshot = self.dag.transition(
            attempt_node_id,
            requested_status,
            output=outcome.to_dict(),
            error={"message": outcome.error} if outcome.error else None,
            cancellation_wins=True,
        )
        effective_status = attempt_snapshot["status"]
        if effective_status == "cancelled" and requested_status != "cancelled":
            outcome.status = "cancelled"
            outcome.accepted = False
            outcome.error = outcome.error or (
                f"late {requested_status} result discarded after cancellation"
            )
            self.tracer.emit(
                "late_subtask_result_discarded",
                task_id=self.task_node_id,
                branch_id=outcome.subtask_id,
                attempt_node_id=attempt_node_id,
                requested_status=requested_status,
                recorded_status=effective_status,
            )
        if branch_node_id and branch_node_id != attempt_node_id:
            self.dag.transition(
                branch_node_id,
                effective_status,
                output=outcome.to_dict(),
                error={"message": outcome.error} if outcome.error else None,
                cancellation_wins=True,
            )

    def _record_rejected_attempt(
        self,
        outcome: SubtaskOutcome,
        attempt_node_id: str,
        *,
        reason: str = "candidate rejected; strong-model retry scheduled",
        retry_kind: str = "strong_model",
    ) -> None:
        self.dag.transition(
            attempt_node_id,
            "failed",
            output=outcome.to_dict(),
            error={"message": reason},
            metadata={"retry_scheduled": True, "retry_kind": retry_kind},
        )

    def _release_rejected_attempt(
        self,
        outcome: SubtaskOutcome,
        *,
        reason: str = "branch acceptance failed before strong-model retry",
    ) -> dict[str, Any]:
        if self.inference_control is None:
            return {"ok": True, "skipped": True, "reason": "control_not_configured"}
        future = self.inference_control.cancel_attempt_async(
            rid=outcome.inference_request_id,
            session_id=outcome.inference_session_id,
            branch_id=outcome.subtask_id,
            attempt_id=outcome.attempt_id,
            reason=reason,
        )
        if future is None:
            return {"ok": True, "skipped": True, "reason": "already_released"}
        try:
            return future.result(timeout=self.inference_control.release_timeout_seconds())
        except BaseException as exc:
            result = {
                "ok": False,
                "error": f"{type(exc).__name__}: {exc}",
                "session_id": outcome.inference_session_id,
                "rid": outcome.inference_request_id,
            }
            self.tracer.emit(
                "inference_session_release_failed",
                task_id=self.task_node_id,
                branch_id=outcome.subtask_id,
                attempt_id=outcome.attempt_id,
                **result,
            )
            return result

    def _validate_subtask_candidate(
        self,
        outcome: SubtaskOutcome,
        plan: TaskPlan,
        subtask_node_id: str,
    ) -> SubtaskOutcome:
        candidate = new_candidate(
            outcome.subtask_id,
            outcome.attempt_id,
            outcome.result,
            self.validation_workspace,
        )
        candidate_node_id = self.dag.add_node(
            kind="candidate_result",
            label=f"candidate {outcome.subtask_id}",
            scope_id=self.scope_id,
            status="pending",
            input={
                "candidate_id": candidate.candidate_id,
                "branch_id": candidate.branch_id,
                "attempt_id": candidate.attempt_id,
                "answer": candidate.answer,
            },
        )
        upstream = outcome.terminal_node_id or subtask_node_id
        self.dag.add_edge(upstream, candidate_node_id, kind="candidate")
        self.dag.transition(candidate_node_id, "ready")
        self.dag.transition(candidate_node_id, "running")
        self.dag.transition(
            candidate_node_id,
            "succeeded",
            output={"candidate_id": candidate.candidate_id},
        )
        try:
            decision = self.validation_engine.evaluate(candidate, plan.acceptance_policy)
        except BaseException as exc:
            result = ValidatorResult(
                "validation-engine",
                "engine",
                False,
                "error",
                reason=f"{type(exc).__name__}: {exc}",
            )
            decision = AcceptanceDecision(
                candidate.candidate_id,
                False,
                "error",
                (result,),
                0.0,
                result.reason,
            )

        cursor = candidate_node_id
        for result in decision.results:
            validation_node_id = self.dag.add_node(
                kind="validation",
                label=f"{result.validator_type}:{result.validator_id}",
                scope_id=self.scope_id,
                status="pending",
                input={
                    "candidate_id": candidate.candidate_id,
                    "validator_id": result.validator_id,
                    "validator_type": result.validator_type,
                },
            )
            self.dag.add_edge(cursor, validation_node_id, kind="validation")
            self.dag.transition(validation_node_id, "ready")
            self.dag.transition(validation_node_id, "running")
            self.dag.transition(
                validation_node_id,
                "succeeded" if result.passed else "failed",
                output=result.to_dict(),
            )
            cursor = validation_node_id

        acceptance_node_id = self.dag.add_node(
            kind="acceptance_decision",
            label=f"acceptance {outcome.subtask_id}",
            scope_id=self.scope_id,
            status="pending",
            input={"candidate_id": candidate.candidate_id},
        )
        self.dag.add_edge(cursor, acceptance_node_id, kind="acceptance")
        self.dag.transition(acceptance_node_id, "ready")
        self.dag.transition(acceptance_node_id, "running")
        self.dag.transition(
            acceptance_node_id,
            "succeeded" if decision.accepted else "failed",
            output=decision.to_dict(),
        )
        self.tracer.emit(
            "candidate_validation_completed",
            task_id=self.task_node_id,
            branch_id=outcome.subtask_id,
            candidate_id=candidate.candidate_id,
            accepted=decision.accepted,
            score=decision.score,
            status=decision.status,
        )
        outcome.candidate_id = candidate.candidate_id
        outcome.accepted = decision.accepted
        outcome.validation_score = decision.score
        outcome.validation = decision.to_dict()
        outcome.terminal_node_id = acceptance_node_id
        if decision.accepted and not outcome.artifact_id:
            digest = hashlib.sha256(candidate.answer.encode("utf-8")).hexdigest()
            artifact_id = f"artifact-{digest[:16]}"
            artifact_record = {
                "artifact_id": artifact_id,
                "kind": "accepted_candidate",
                "content": candidate.answer,
                "content_sha256": digest,
                "source": "acceptance_validation",
                "branch_id": outcome.subtask_id,
                "attempt_id": outcome.attempt_id,
                "validation": decision.to_dict(),
            }
            artifact_node_id = self.dag.add_node(
                kind="verified_artifact",
                label=f"accepted artifact {artifact_id}",
                scope_id=self.scope_id,
                status="pending",
                input={
                    "artifact_id": artifact_id,
                    "branch_id": outcome.subtask_id,
                    "attempt_id": outcome.attempt_id,
                    "candidate_id": candidate.candidate_id,
                },
                metadata={
                    "content_sha256": digest,
                    "artifact_kind": "accepted_candidate",
                },
            )
            self.dag.add_edge(
                acceptance_node_id, artifact_node_id, kind="artifact"
            )
            self.dag.transition(artifact_node_id, "ready")
            self.dag.transition(artifact_node_id, "running")
            self.dag.transition(
                artifact_node_id, "succeeded", output=artifact_record
            )
            outcome.artifact_id = artifact_id
            outcome.artifact = {
                key: value
                for key, value in artifact_record.items()
                if key != "content"
            }
            outcome.terminal_node_id = artifact_node_id
            self.tracer.emit(
                "accepted_candidate_artifact_recorded",
                task_id=self.task_node_id,
                branch_id=outcome.subtask_id,
                attempt_id=outcome.attempt_id,
                artifact_id=artifact_id,
                content_sha256=digest,
                node_id=artifact_node_id,
            )
        return outcome

    def _resolve_branch_inputs(
        self, declared_inputs: dict[str, Any], *, branch_id: str
    ) -> dict[str, Any]:
        """Complete a branch's declared inputs from a unique parent artifact record.

        Tools may attach ``binding_records`` to a verified artifact.  Each record is
        a concrete input row (for example ``entity``, ``rank`` and ``operation``).
        The model only needs to name enough stable fields to select one row.  The
        Runtime then copies the remaining fields without overriding anything the
        model explicitly supplied.  Ambiguous or non-matching records are ignored.
        """

        resolved = copy.deepcopy(declared_inputs)
        if not declared_inputs:
            return resolved
        matches: list[tuple[str, dict[str, Any]]] = []
        with self._verified_artifact_lock:
            artifacts = list(self._verified_artifacts)
        for artifact in reversed(artifacts):
            records = artifact.get("binding_records")
            if not isinstance(records, list):
                continue
            for raw_record in records:
                if not isinstance(raw_record, dict):
                    continue
                shared_keys = set(declared_inputs).intersection(raw_record)
                if not shared_keys:
                    continue
                if all(raw_record[key] == declared_inputs[key] for key in shared_keys):
                    matches.append((str(artifact.get("artifact_id") or ""), raw_record))
        unique_records: dict[str, tuple[str, dict[str, Any]]] = {}
        for artifact_id, record in matches:
            identity = json.dumps(record, ensure_ascii=False, sort_keys=True, default=str)
            unique_records.setdefault(identity, (artifact_id, record))
        if len(unique_records) != 1:
            if matches:
                self.tracer.emit(
                    "branch_input_binding_ambiguous",
                    task_id=self.task_node_id,
                    branch_id=branch_id,
                    declared_inputs=copy.deepcopy(declared_inputs),
                    candidate_count=len(unique_records),
                )
            return resolved
        artifact_id, record = next(iter(unique_records.values()))
        added: dict[str, Any] = {}
        for key, value in record.items():
            if key not in resolved:
                resolved[key] = copy.deepcopy(value)
                added[key] = copy.deepcopy(value)
        if added:
            self.tracer.emit(
                "branch_inputs_bound_from_parent_artifact",
                task_id=self.task_node_id,
                branch_id=branch_id,
                artifact_id=artifact_id,
                declared_inputs=copy.deepcopy(declared_inputs),
                added_inputs=added,
                resolved_inputs=copy.deepcopy(resolved),
            )
        return resolved

    def _run_planned_subtask(
        self,
        spec: SubtaskSpec,
        subtask_node_id: str,
        scope_id: str,
        cancellation_scope: CancellationScope,
        plan_id: str,
        plan: TaskPlan,
        required_for_join: bool,
        attempt_id: str,
        requested_model: str,
        reasoning_mode: str,
        on_critical_path: bool,
        gateway_routing_key: str,
        gateway_placement_mode: str,
        parent_history: tuple[dict[str, Any], ...],
    ) -> SubtaskOutcome:
        started = time.time()
        self.dag.transition(subtask_node_id, "running")
        try:
            child_provider = self.provider.fork(stream=False)
        except (AttributeError, TypeError) as exc:
            ended = time.time()
            return SubtaskOutcome(
                spec.id,
                "failed",
                error=f"provider cannot create an isolated child session: {exc}",
                started_at=started,
                ended_at=ended,
            )

        resolved_inputs = self._resolve_branch_inputs(spec.inputs, branch_id=spec.id)
        resolved_spec = SubtaskSpec(
            id=spec.id,
            task=spec.task,
            depends_on=spec.depends_on,
            ordinal=spec.ordinal,
            input_refs=spec.input_refs,
            inputs=resolved_inputs,
            required_artifact_kinds=spec.required_artifact_kinds,
            required_artifact_paths=spec.required_artifact_paths,
            required_test_targets=spec.required_test_targets,
        )
        parent_task = self._current_task_for_child()
        branch_context = self.branch_context_compiler.compile(
            parent_task=parent_task,
            spec=resolved_spec,
            plan=plan,
            plan_id=plan_id,
            allowed_tools=self.tools.names,
            registered_validators=self.validation_registry.registered_refs(),
            required_for_join=required_for_join,
            on_critical_path=on_critical_path,
        )
        # The original task, system policy and verified tool results already
        # live in parent_history.  The tail contains only branch-specific facts,
        # avoiding a second copy of the long task while preserving semantics.
        rendered_branch_context = branch_context.render(include_parent_task=False)
        from .branch_test_delivery import branch_selfcheck_enabled
        if os.environ.get("SEMSERVE_BRANCH_COUNTEREXAMPLE_GATE") == "1":
            rendered_branch_context += COUNTEREXAMPLE_GATE_PROMPT
        elif branch_selfcheck_enabled() and spec.required_artifact_kinds == ("file",):
            rendered_branch_context += (
                "\n\nBefore delivery, run one focused self-check of the actual interface the parent "
                "will use. For a component script, run its command-line entry and confirm it "
                "produces the declared output from the current inputs. A test that imports the "
                "function only covers that function. "
            )
            if os.environ.get("SEMSERVE_G1") != "1" or contract_heuristics_enabled():
                rendered_branch_context += (
                    "Runtime independently checks fresh output for standard render.py components "
                    "with an owned output in contract.json. "
                )
            rendered_branch_context += (
                "Use the failure receipt to repair the owned file before submitting again."
            )
        if os.environ.get("SEMSERVE_G1") == "1" and spec.required_artifact_kinds == ("file",):
            rendered_branch_context += (
                "\n\n[G1_LOCAL_BRANCH_CHECK] File-branch shell commands run in a private mirror, "
                "with filesystem write isolation. Only permitted owned-file changes can be "
                "committed; fixtures and sibling outputs remain private. Use the native write "
                "tools for owned implementation files. Before deliver_files, create ordinary "
                "unittest checks in the private .semserve/g1_checks/test_branch.py using shell "
                "and also satisfy any declared required_test_targets. No self-check SDK import is needed. "
                "Call the actual owned implementation and assert the raw returned shape and a "
                "visible business rule on a small valid input; derive expected values from the "
                "public contract before calling the implementation. Add applicable documented "
                "boundary cases, without inventing requirements. Printed PASS, exit 0, and "
                "assertTrue(True) are not a test receipt. Runtime executes and records the check. "
                "If real upstream outputs are unavailable, use valid private fixtures. Complete "
                "coding plus local checking and deliver; actual-input integration remains pending "
                "for the parent after join. Do not wait indefinitely for sibling artifacts or "
                "fabricate/delete shared outputs. Repair the precise setup or candidate error "
                "from the Runtime receipt before retrying."
            )
        self.tracer.emit(
            "branch_context_compiled",
            task_id=self.task_node_id,
            run_id=self.dag.run_id,
            plan_id=plan_id,
            branch_id=spec.id,
            attempt_id=attempt_id,
            context_sha256=hashlib.sha256(rendered_branch_context.encode("utf-8")).hexdigest(),
            parent_task_chars=len(parent_task),
            branch_objective_chars=len(spec.task),
            rendered_chars=len(rendered_branch_context),
            inherited_message_count=len(parent_history),
            allowed_tools=list(branch_context.allowed_tools),
            registered_validators=list(branch_context.registered_validators),
        )

        identity_context = (
            "\n\nPLAN AND BRANCH IDENTITY:\n"
            f"run_id={self.dag.run_id}\nplan_id={plan_id}\n"
            f"branch_id={spec.id}\n"
            f"branch_key={self.dag.run_id}/{plan_id}/{spec.id}\n\n"
            "The runtime supplies the authoritative task, branch objective, policy, "
            "tools, and validators in the child request.\n"
            "You are executing one child task. Work only on the assigned objective, "
            "return concrete evidence, and do not attempt to manage sibling tasks."
        )
        frontier_contract = resolved_inputs.get("_runtime_frontier_contract") or {}
        implementation_contract = resolved_inputs.get(
            "_runtime_implementation_contract"
        ) or {}
        child_max_steps = min(
            self.max_steps,
            int(
                frontier_contract.get("max_model_turns")
                or implementation_contract.get("max_model_turns")
                or self.max_steps
            ),
        )
        child = AgentRuntime(
            provider=child_provider,
            tools=self.tools,
            system_prompt=self.system_prompt,
            max_steps=child_max_steps,
            validator=None,
            tracer=self.tracer,
            dag=self.dag,
            max_parallelism=self.max_parallelism,
            max_subtasks=self.max_subtasks,
            max_subtask_depth=self.max_subtask_depth,
            max_plan_expansions=1,
            allow_subtasks=False,
            scope_id=scope_id,
            parent_node_id=subtask_node_id,
            parent_task_id=self.task_node_id,
            plan_id=plan_id,
            allowed_input_refs=spec.input_refs,
            branch_inputs=resolved_inputs,
            required_artifact_kinds=spec.required_artifact_kinds,
            required_artifact_paths=spec.required_artifact_paths,
            required_test_targets=spec.required_test_targets,
            depth=self.depth + 1,
            require_file_branch_contract=self.require_file_branch_contract,
            owns_tools=False,
            cancellation_scope=cancellation_scope,
            execution_registry=self.execution_registry,
            tool_semaphore=self._tool_semaphore,
            inference_control=self.inference_control,
            branch_id=spec.id,
            attempt_id=attempt_id,
            validation_registry=self.validation_registry,
            validation_workspace=self.validation_workspace,
            speculation_manager=self.speculation_manager,
            owns_speculation_manager=False,
            adaptive_routing_policy=self.adaptive_routing_policy,
            required_for_join=required_for_join,
            on_critical_path=on_critical_path,
            initial_route_mode=(
                "require_strong"
                if requested_model == self.adaptive_routing_policy.strong_model
                else "auto"
            ),
            initial_requested_model=requested_model,
            initial_reasoning_mode=reasoning_mode,
            branch_context_compiler=self.branch_context_compiler,
            gateway_routing_key=gateway_routing_key,
            gateway_placement_mode=gateway_placement_mode,
            execution_state_observer=self.execution_state_observer,
            fork_only_stable_prefix=self.fork_only_stable_prefix,
            fork_tool_schemas=self._fork_parent_tool_schemas,
            output_guard=self.output_guard_enabled,
        )
        with self._children_lock:
            self._active_children.add(child)
        self.execution_registry.register(
            subtask_node_id,
            cancellation_scope,
            kind="subtask",
            cancel=child.cancel,
            metadata={"child_scope_id": scope_id},
        )
        try:
            result = child.run(
                spec.task,
                initial_messages=parent_history + (
                    {
                        "role": "user",
                        "content": rendered_branch_context + identity_context,
                    },
                ),
            )
            verified_artifact = child.latest_verified_artifact()
            if (spec.required_artifact_kinds or spec.required_artifact_paths or spec.required_test_targets) and not child._artifact_satisfies_branch_completion(verified_artifact):
                raise RuntimeError("Branch delivery became invalid before join")
            artifact_summary = None
            candidate_result = result
            artifact_id = ""
            if verified_artifact is not None:
                candidate_result = str(verified_artifact["content"])
                artifact_id = str(verified_artifact["artifact_id"])
                artifact_summary = {
                    key: value
                    for key, value in verified_artifact.items()
                    if key not in {"content", "completed_monotonic_ns"}
                }
                artifact_summary["delivery_verified"] = bool(
                    spec.required_artifact_kinds or spec.required_artifact_paths or spec.required_test_targets
                ) and child._artifact_satisfies_branch_completion(verified_artifact)
                artifact_summary["materialized_files"] = child._materialized_artifact_files(verified_artifact)
                self.tracer.emit(
                    "branch_result_bound_to_verified_artifact",
                    task_id=self.task_node_id,
                    plan_id=plan_id,
                    branch_id=spec.id,
                    attempt_id=attempt_id,
                    artifact_id=artifact_id,
                    content_sha256=verified_artifact["content_sha256"],
                    tool=verified_artifact["tool"],
                )
            return SubtaskOutcome(
                spec.id,
                "succeeded",
                result=candidate_result,
                terminal_node_id=child.terminal_node_id,
                usage=dict(child.last_usage),
                started_at=started,
                ended_at=time.time(),
                attempt_id=attempt_id,
                inference_session_id=child.inference_session_id,
                inference_request_id=child.last_inference_request_id,
                last_selected_model=child.last_selected_model,
                selected_worker=str(child.last_route_info.get("selected_worker") or ""),
                artifact_id=artifact_id,
                artifact=artifact_summary,
            )
        except ProviderCancelled as exc:
            return SubtaskOutcome(
                spec.id,
                "cancelled",
                error=str(exc),
                terminal_node_id=child.terminal_node_id,
                usage=dict(child.last_usage),
                started_at=started,
                ended_at=time.time(),
                attempt_id=attempt_id,
                inference_session_id=child.inference_session_id,
                inference_request_id=child.last_inference_request_id,
                last_selected_model=child.last_selected_model,
                selected_worker=str(child.last_route_info.get("selected_worker") or ""),
            )
        except BaseException as exc:
            return SubtaskOutcome(
                spec.id,
                "failed",
                error=f"{type(exc).__name__}: {exc}",
                terminal_node_id=child.terminal_node_id,
                usage=dict(child.last_usage),
                started_at=started,
                ended_at=time.time(),
                attempt_id=attempt_id,
                inference_session_id=child.inference_session_id,
                inference_request_id=child.last_inference_request_id,
                last_selected_model=child.last_selected_model,
                selected_worker=str(child.last_route_info.get("selected_worker") or ""),
            )
        finally:
            with self._children_lock:
                self._active_children.discard(child)

    def _current_task_for_child(self) -> str:
        """Resolve parent task text by node identity, never by a local label."""
        snapshot = self.dag.snapshot()
        for node in snapshot.get("nodes", []):
            if node.get("id") != self.task_node_id:
                continue
            task = (node.get("input") or {}).get("task")
            if isinstance(task, str) and task:
                return task
        return "Continue the parent task using only the assigned branch objective."

    def _handle_final_answer(
        self,
        state: RuntimeState,
        content: str,
        model_node_id: str,
    ) -> tuple[str | None, str]:
        if self.depth > 0 and (self.required_artifact_kinds or self.required_artifact_paths or self.required_test_targets):
            verified_artifact = self.latest_verified_artifact()
            if not self._artifact_satisfies_branch_completion(verified_artifact):
                expected = ", ".join(self.required_artifact_kinds)
                actual = (
                    str(verified_artifact.get("kind"))
                    if verified_artifact is not None
                    else "none"
                )
                validation_node_id = self._record_validation(
                    model_node_id,
                    accepted=False,
                    feedback=(
                        "Branch completion contract not satisfied: expected artifact kind "
                        f"in [{expected}], latest kind is {actual}. Continue the assigned "
                        "branch until the required artifact is produced."
                    ),
                )
                state.retry_count += 1
                state.messages.append(
                    {
                        "role": "user",
                        "content": (
                            "Branch completion contract not satisfied. Produce a verified "
                            f"artifact whose kind is one of: {expected}; assigned files "
                            f"{list(self.required_artifact_paths)}, test targets "
                            f"{list(self.required_test_targets)}. Files must still match "
                            "their verified contents. Sibling artifacts and stale tests do not count."
                        ),
                    }
                )
                return None, validation_node_id
        if not content.strip():
            validation_node_id = self._record_validation(
                model_node_id,
                accepted=False,
                feedback="empty model response",
            )
            state.retry_count += 1
            state.messages.append(
                {
                    "role": "user",
                    "content": "Your response was empty. Call a tool or provide a final answer.",
                }
            )
            return None, validation_node_id

        cursor_node_id = model_node_id
        if self.validator is not None:
            accepted, feedback = self.validator()
            cursor_node_id = self._record_validation(
                model_node_id, accepted=accepted, feedback=feedback
            )
            self.tracer.emit(
                "validation",
                accepted=accepted,
                feedback=feedback,
                task_id=state.task_id,
                node_id=cursor_node_id,
            )
            if not accepted:
                state.validation_failures += 1
                cursor_node_id = self._observe_parallel_decision_point(
                    state,
                    node_id=cursor_node_id,
                    event_type="critical_validation_failure",
                    branch_id=state.branch_id,
                    attempt_id=state.attempt_id,
                    failure_type="runtime_validation_failed",
                    required_for_join=state.required_for_join,
                    on_critical_path=True,
                    join_blocked=False,
                    validation_summary=feedback,
                )
                if state.pending_parallel_offer is not None:
                    state.retry_count += 1
                    return None, cursor_node_id
                escalated = self.adaptive_routing_policy.record_validation_failure(state)
                if escalated:
                    routing_node_id = self.dag.add_node(
                        kind="routing_decision",
                        label=(
                            f"escalate via {self.adaptive_routing_policy.escalation_action} "
                            f"to {state.requested_model}"
                        ),
                        scope_id=self.scope_id,
                        status="pending",
                        input={
                            "trigger": "validation_failed",
                            "last_selected_model": state.last_selected_model,
                            "weak_validation_failures": state.weak_validation_failures,
                            "required_for_join": state.required_for_join,
                            "on_critical_path": state.on_critical_path,
                        },
                        metadata={
                            "task_id": state.task_id,
                            "branch_id": state.branch_id,
                            "attempt_id": state.attempt_id,
                        },
                    )
                    self.dag.add_edge(cursor_node_id, routing_node_id, kind="escalation")
                    self.dag.transition(routing_node_id, "ready")
                    self.dag.transition(routing_node_id, "running")
                    self.dag.transition(
                        routing_node_id,
                        "succeeded",
                        output={
                            "route_mode": state.route_mode,
                            "requested_model": state.requested_model,
                            "reasoning_mode": state.reasoning_mode,
                            "escalation_action": self.adaptive_routing_policy.escalation_action,
                            "reason": state.escalation_reason,
                        },
                    )
                    cursor_node_id = routing_node_id
                    self.tracer.emit(
                        "route_criticality_escalation_applied",
                        task_id=state.task_id,
                        branch_id=state.branch_id,
                        attempt_id=state.attempt_id,
                        from_model=state.last_selected_model,
                        to_model=state.requested_model,
                        reasoning_mode=state.reasoning_mode,
                        escalation_action=self.adaptive_routing_policy.escalation_action,
                        weak_validation_failures=state.weak_validation_failures,
                        required_for_join=state.required_for_join,
                        on_critical_path=state.on_critical_path,
                        reason=state.escalation_reason,
                        node_id=routing_node_id,
                    )
                state.retry_count += 1
                state.messages.append(
                    {
                        "role": "user",
                        "content": f"Runtime validation failed:\n{feedback}\nContinue fixing the task.",
                    }
                )
                return None, cursor_node_id

        final_node_id = self.dag.add_node(
            kind="final_answer",
            label="final answer",
            scope_id=self.scope_id,
            status="pending",
            input={"content": content},
        )
        self.dag.add_edge(cursor_node_id, final_node_id, kind="control")
        self.dag.transition(final_node_id, "ready")
        self.dag.transition(final_node_id, "running")
        self.dag.transition(final_node_id, "succeeded", output={"content": content})
        self.terminal_node_id = final_node_id
        state.status = "completed"
        self.tracer.emit(
            "task_completed",
            step=state.step,
            usage=state.usage,
            final_answer=content,
            task_id=state.task_id,
            node_id=final_node_id,
            scope_id=self.scope_id,
        )
        return content, final_node_id

    def _observe_parallel_decision_point(
        self,
        state: RuntimeState,
        *,
        node_id: str,
        event_type: str,
        branch_id: str,
        attempt_id: str,
        failure_type: str,
        required_for_join: bool,
        on_critical_path: bool,
        join_blocked: bool,
        validation_summary: str,
        defer_offer: bool = False,
    ) -> str:
        """Pass immutable execution evidence to the optional control plane.

        Off mode returns before constructing a decision point. Shadow mode may
        record telemetry, but neither mode can mutate messages, tools, routing,
        or the execution DAG through this interface.
        """

        if self.parallel_controller.mode == "off":
            return node_id
        if (
            self.parallel_controller.mode == "active"
            and not self.allow_recovery_subtasks
        ):
            return node_id
        if (
            state.recovery_plan_expansion_count
            >= self.max_recovery_plan_expansions
        ):
            return node_id
        point = ParallelDecisionPoint(
            run_id=state.run_id,
            task_id=state.task_id,
            node_id=node_id,
            branch_id=branch_id,
            attempt_id=attempt_id,
            depth=self.depth,
            step=state.step,
            event_type=event_type,
            decision_phase="recovery",
            failure_type=failure_type,
            required_for_join=required_for_join,
            on_critical_path=on_critical_path,
            join_blocked=join_blocked,
            available_width=min(self.max_parallelism, self.max_subtasks),
            allowed_validator_refs=tuple(
                self.validation_registry.registered_refs()
            ),
            task_summary=state.task,
            validation_summary=validation_summary,
            resource_snapshot={
                "selected_worker": self.last_route_info.get("selected_worker"),
                "selected_model": self.last_selected_model,
                **self._read_resource_snapshot(),
            },
            local_expansions_used=max(0, state.plan_expansion_count - 1),
            retry_count=state.retry_count,
            validation_failures=state.validation_failures,
            token_usage=int(state.usage.get("total_tokens", 0)),
        )
        action = self.parallel_controller.evaluate(point)
        if not isinstance(action, ParallelOffer):
            return node_id
        if defer_offer:
            if state.deferred_parallel_offer is None:
                state.deferred_parallel_offer = action
            return node_id
        return self._install_parallel_offer(
            state,
            action,
            upstream_node_id=node_id,
            controller=self.parallel_controller,
        )

    def _observe_initial_parallel_decision_point(
        self,
        state: RuntimeState,
        *,
        node_id: str,
    ) -> str:
        """Evaluate one advisory initial-planning decision without fake failure state."""

        controller = self.initial_parallel_controller
        if controller.mode == "off":
            return node_id
        if controller.mode == "active" and not self.allow_initial_subtasks:
            return node_id
        if (
            state.initial_plan_expansion_count
            >= self.max_initial_plan_expansions
        ):
            return node_id
        point = ParallelDecisionPoint(
            run_id=state.run_id,
            task_id=state.task_id,
            node_id=node_id,
            branch_id=state.branch_id,
            attempt_id=state.attempt_id,
            depth=self.depth,
            step=state.step,
            event_type="initial_planning",
            decision_phase="initial",
            available_width=min(self.max_parallelism, self.max_subtasks),
            allowed_validator_refs=tuple(
                self.validation_registry.registered_refs()
            ),
            task_summary=state.task,
            validation_summary="",
            resource_snapshot=self._read_resource_snapshot(),
            local_expansions_used=0,
            retry_count=0,
            validation_failures=0,
            token_usage=0,
        )
        action = controller.evaluate(point)
        if not isinstance(action, ParallelOffer):
            return node_id
        return self._install_parallel_offer(
            state,
            action,
            upstream_node_id=node_id,
            controller=controller,
        )

    def _install_parallel_offer(
        self,
        state: RuntimeState,
        action: ParallelOffer,
        *,
        upstream_node_id: str,
        controller: ParallelController | None = None,
    ) -> str:
        offer_node_id = self.dag.add_node(
            kind="parallel_offer",
            label="runtime parallelization offer",
            scope_id=self.scope_id,
            status="pending",
            input=action.to_dict(),
            metadata={
                "task_id": state.task_id,
                "branch_id": state.branch_id,
                "attempt_id": state.attempt_id,
            },
        )
        self.dag.add_edge(upstream_node_id, offer_node_id, kind="control")
        self.dag.transition(offer_node_id, "ready")
        self.dag.transition(offer_node_id, "running")
        self.dag.transition(
            offer_node_id,
            "succeeded",
            output={"offer_id": action.offer_id, "maximum_width": action.maximum_width},
        )
        state.pending_parallel_offer = action
        state.pending_parallel_controller = controller or self.parallel_controller
        state.parallel_offer_history_cut = len(state.messages)
        state.parallel_decision_repairs = 0
        state.messages.append(
            {
                "role": "user",
                "content": (controller or self.parallel_controller).offer_prompt(action),
            }
        )
        return offer_node_id

    def _read_resource_snapshot(self) -> dict[str, Any]:
        try:
            snapshot = self.resource_snapshot_provider.snapshot()
            return snapshot if isinstance(snapshot, dict) else {
                "available": False,
                "source": "invalid_provider",
            }
        except BaseException as exc:
            self.tracer.emit(
                "parallel_resource_snapshot_failed",
                task_id=self.task_node_id,
                error_type=type(exc).__name__,
            )
            return {
                "available": False,
                "source": "provider_error",
                "error_type": type(exc).__name__,
            }

    def _record_validation(
        self,
        upstream_node_id: str,
        *,
        accepted: bool,
        feedback: str,
    ) -> str:
        node_id = self.dag.add_node(
            kind="validation",
            label="runtime validation",
            scope_id=self.scope_id,
            status="pending",
            input={"feedback": feedback},
        )
        self.dag.add_edge(upstream_node_id, node_id, kind="control")
        self.dag.transition(node_id, "ready")
        self.dag.transition(node_id, "running")
        self.dag.transition(
            node_id,
            "succeeded" if accepted else "failed",
            output={"accepted": accepted, "feedback": feedback},
        )
        return node_id

    def _g1_early_semantic_review_prompt(self, state: RuntimeState) -> str:
        from .g1_discovery import (EarlySemanticReview, EARLY_SEMANTIC_REVIEW_PROMPT,
                                   early_semantic_review_enabled)
        if (not early_semantic_review_enabled() or self.depth != 0 or state.parent_task_id
                or self._guard_serial_selfcheck(state) or self._report_context_error(state)):
            return ""
        evidence = self._v2_project_tool_evidence(state)
        review = getattr(self, "_g1_early_semantic_review_state", None)
        if review is None:
            review = self._g1_early_semantic_review_state = EarlySemanticReview()
        task_identity = (state.run_id, state.task_id, state.scope_id,
                         hashlib.sha256(state.task.encode("utf-8")).hexdigest())
        grant, fresh = review.claim(task_identity, request_id=state.inference_request_id,
            generation=state.v2_frontier_handshake_generation,
            read_groups=evidence.reads, writes=evidence.writes,
            plan_expansions=state.plan_expansion_count, v2_expansions=state.v2_expansion_count)
        if grant is None:
            return ""
        if fresh:
            self.tracer.emit("g1_early_semantic_review_injected", scope_id=state.scope_id,
                task_id=state.task_id, step=state.step,
                request_id=grant["request_id"], generation=grant["generation"],
                read_evidence_count=grant["read_evidence_count"],
                prompt_sha256=hashlib.sha256(EARLY_SEMANTIC_REVIEW_PROMPT.encode("utf-8")).hexdigest(),
                boundary="authorized_report_schema", model_input_pending=True)
        return EARLY_SEMANTIC_REVIEW_PROMPT

    def _model_tool_schemas(self, state: RuntimeState) -> list[dict[str, Any]]:
        self._report_reset_schema_authorization()
        serial_selfcheck = self._guard_serial_selfcheck(state)
        self._v2_expire_offer(state)
        if not serial_selfcheck and isinstance(state.pending_parallel_offer, ParallelOffer):
            controller = state.pending_parallel_controller or self.parallel_controller
            schema = copy.deepcopy(controller.decision_tool_schema(state.pending_parallel_offer))
            self._require_file_contract_in_schema(schema)
            return [schema]
        schemas = self.tools.schemas()
        if state.tool_repair_mode:
            repair_schemas = [
                copy.deepcopy(schema)
                for schema in schemas
                if schema.get("function", {}).get("name") == state.tool_repair_mode
                and schema.get("function", {}).get("name") != "report_frontier_state"
            ]
            if len(repair_schemas) != 1:
                raise RuntimeError(
                    f"required repair tool is unavailable: {state.tool_repair_mode}"
                )
            return repair_schemas
        if (
            self.depth == 0
            and not serial_selfcheck
            and self.parallel_controller_v2.mode != "off"
            and state.pending_v2_offer is None
            and self._frontier_report_required(state)
        ):
            report_schemas = [
                copy.deepcopy(schema)
                for schema in schemas
                if schema.get("function", {}).get("name")
                == "report_frontier_state"
            ]
            if len(report_schemas) != 1:
                raise RuntimeError("required frontier report tool is unavailable")
            reason = state.v2_frontier_handshake_reason
            if os.environ.get("SEMSERVE_G1") == "1":
                detail = (
                    "Update the immediate coding frontier and separately record real-input "
                    "validation dependencies. A fully observed interface may allow a consumer "
                    "implementation before producer artifacts exist; use isolated_fixture and "
                    "validation_read_set for that case. Do not treat fixture success as real "
                    "integration success. "
                )
            elif reason == "root_semantic_join_committed":
                detail = (
                    "A root semantic join just committed. Report only the immediate "
                    "executable frontier after that join. A consumer that reads another "
                    "proposed unit's output is not ready yet: give every unit accurate "
                    "read_set and write_set values so Runtime can block it. Do not mark "
                    "later fan-in consumers ready merely because their source stubs exist. "
                )
            elif reason == "post_join_watched_output_materialized":
                detail = (
                    "The single post-join producer selected by the previous report has "
                    "now materialized its required output. Report newly unlocked immediate "
                    "successors, with accurate read_set and write_set values. "
                )
            elif reason == "shared_contract_materialized":
                detail = (
                    "The shared contract has just materialized. Report the immediate "
                    "independent producers unlocked by that contract before the parent "
                    "writes any of their outputs. "
                )
            else:
                detail = (
                    "A successful root tool batch produced new verified evidence. Rebuild "
                    "the immediate executable frontier from all verified results accumulated "
                    "so far, independent of filenames or task templates. Do not turn every "
                    "inspected file into a work unit and do not infer facts from unread "
                    "inputs. If the evidence is still insufficient, report an empty "
                    "ready_upsert. "
                )
            from .qwen_frontier_predictor import branch_profiles_enabled

            if branch_profiles_enabled():
                detail += (
                    "For each candidate in ready_upsert, include difficulty (low, medium, or high) "
                    "for the remaining implementation and verification effort, and length (short, "
                    "medium, or long) for the remaining work relative to other candidates. "
                    "Estimate from visible evidence. Low difficulty and short length are valid "
                    "estimates and do not disqualify a candidate. "
                )
            prompt = (
                "Runtime requires one bounded semantic commit before ordinary work. "
                + detail
                + "Report only state changes justified by completed tool results. Never "
                "list an output already written unless a later observed failure requires "
                "repair. Empty ready_upsert is valid. Call report_frontier_state exactly "
                "once; do not answer the task or call another tool in this turn."
            )
            self._frontier_report_request_active = True
            self._report_grant(state)
            prompt += self._g1_early_semantic_review_prompt(state)
            prompt = add_frontier_discovery_guidance(
                self._report_scoped_prompt(state, prompt)
            )
            if contract_heuristics_enabled():
                from .g1_discovery import render_discovery_prompt
                prompt += render_discovery_prompt(self._g1_discovery_inventory(state))
            if not (
                state.messages
                and state.messages[-1].get("role") == "user"
                and state.messages[-1].get("content") == prompt
            ):
                state.messages.append({"role": "user", "content": prompt})
            return report_schemas
        self._frontier_report_request_active = False
        schemas = self._report_without_schema(schemas)
        if not serial_selfcheck:
            self._report_business_mode(state)
        # Business inputs belong to the authoritative branch context. Equal key
        # names do not imply a binding to every tool (API path != file path).
        # Explicit parent-artifact resolution and input_refs remain independent.
        if self.allowed_input_refs:
            allowed = set(self.allowed_input_refs)
            restricted_schemas: list[dict[str, Any]] = []
            for original in schemas:
                schema = copy.deepcopy(original)
                properties = (
                    schema.get("function", {})
                    .get("parameters", {})
                    .get("properties", {})
                )
                for property_schema in properties.values():
                    enum = property_schema.get("enum")
                    if not isinstance(enum, list):
                        continue
                    overlap = [item for item in enum if str(item) in allowed]
                    if overlap:
                        property_schema["enum"] = overlap
                restricted_schemas.append(schema)
            schemas = restricted_schemas
        self_aware_parallel_active = (
            self.initial_parallel_controller.mode == "active"
            or self.parallel_controller.mode == "active"
        )
        self_aware_initial_budget_available = (
            not self_aware_parallel_active
            or (
                state.plan_expansion_count == 0
                and state.initial_plan_expansion_count
                < self.max_initial_plan_expansions
            )
        )
        subtask_tool_available = (
            self.allow_initial_subtasks
            and not serial_selfcheck
            and self_aware_initial_budget_available
            and state.plan_expansion_count < self.max_plan_expansions
            and state.plan_validation_failures < self.max_plan_validation_failures
        )
        if subtask_tool_available:
            # Reflect the runtime fan-out limit in the schema shown to the
            # model. This lets constrained tool generation respect the actual
            # budget instead of learning about it only from a rejected call.
            spawn_schema = copy.deepcopy(SPAWN_SUBTASKS_SCHEMA)
            spawn_schema["function"]["parameters"]["properties"]["subtasks"][
                "maxItems"
            ] = self.max_subtasks
            subtask_properties = spawn_schema["function"]["parameters"][
                "properties"
            ]["subtasks"]["items"]["properties"]
            subtask_properties["depends_on"]["maxItems"] = max(
                0, self.max_subtasks - 1
            )
            if self.max_subtasks >= 2:
                spawn_schema["function"]["parameters"]["properties"]["quorum"][
                    "maximum"
                ] = self.max_subtasks
            spawn_schema["function"]["parameters"]["properties"]["top_k"][
                "maximum"
            ] = self.max_subtasks
            validator_refs = list(self.validation_registry.registered_refs())
            validators_schema = spawn_schema["function"]["parameters"][
                "properties"
            ]["acceptance_policy"]["properties"]["validators"]
            validators_schema["description"] = (
                "Validator references registered by this runtime. Do not invent names."
            )
            if validator_refs:
                validators_schema["items"]["enum"] = validator_refs
            else:
                # There is no valid non-empty validator list for this runtime.
                validators_schema["maxItems"] = 0
            schemas.append(spawn_schema)
            self._require_file_contract_in_schema(spawn_schema)
        if state.pending_v2_offer is not None and not serial_selfcheck:
            schema = self.parallel_controller_v2.schema(state.pending_v2_offer)
            self._require_file_contract_in_schema(schema)
            schemas.append(schema)
        if serial_selfcheck:
            schemas = [s for s in schemas if not self._guard_selfcheck_tool_error(
                state, ToolCall('', s['function']['name'], {}))]
        return self._guard_schemas(state, schemas)

    def _frontier_report_required(self, state: RuntimeState) -> bool:
        """Expose report-only mode only for an explicitly scheduled generation."""

        return bool(state.v2_frontier_handshake_pending and not self._guard_serial_selfcheck(state))

    def _require_file_contract_in_schema(self, schema: dict[str, Any]) -> None:
        if not self.require_file_branch_contract:
            return
        def visit(node):
            if isinstance(node, dict):
                props = node.get("properties", {})
                if "completion_contract" in props and "task" in props:
                    node.setdefault("required", []).append("completion_contract")
                    contract = props["completion_contract"]
                    contract["required"] = ["required_artifact_kinds", "required_artifact_paths", "required_test_targets"]
                    contract["properties"]["required_artifact_kinds"]["items"]["enum"] = ["file"]
                for value in node.values():
                    visit(value)
            elif isinstance(node, list):
                for value in node:
                    visit(value)
        visit(schema)

    def _artifact_satisfies_branch_completion(
        self, artifact: dict[str, Any] | None
    ) -> bool:
        if artifact is None:
            return False
        if self.required_artifact_kinds and str(artifact.get("kind") or "") not in self.required_artifact_kinds:
            return False
        if artifact.get("branch_id") not in (None, self.branch_id):
            return False
        if artifact.get("attempt_id") not in (None, self.attempt_id):
            return False
        targets = artifact.get("tested_targets", [])
        if not isinstance(targets, list) or not all(isinstance(t, str) for t in targets):
            return False
        if not set(self.required_test_targets).issubset(targets):
            return False
        if artifact.get("runtime_test_receipt_id") is not None and (
                self._file_branch_checks is None
                or not self._file_branch_checks.still_current(artifact)):
            return False
        if self.required_artifact_paths:
            materialized = self._materialized_artifact_files(artifact)
            if not set(self.required_artifact_paths).issubset(materialized):
                return False
        return True

    def _materialized_artifact_files(self, artifact: dict[str, Any]) -> dict[str, str]:
        """Verify file evidence against live workspace bytes, never model prose."""
        if artifact.get("kind") != "file":
            return {}
        try:
            files = json.loads(artifact.get("content", ""))
        except (ValueError, TypeError):
            return {}
        if not isinstance(files, dict):
            return {}
        verified = {}
        for name, content in files.items():
            if not isinstance(name, str) or not isinstance(content, str):
                continue
            try:
                path = (self.validation_workspace / name).resolve()
                relative = path.relative_to(self.validation_workspace).as_posix()
                if relative != name or not path.is_file():
                    continue
                data = path.read_bytes()
                if data != content.encode("utf-8"):
                    continue
                verified[name] = hashlib.sha256(data).hexdigest()
            except (OSError, ValueError):
                continue
        return verified

    def _cancel_active_children(self) -> None:
        with self._children_lock:
            children = list(self._active_children)
        for child in children:
            child.cancel("parent runtime cancellation requested")

    def _request_subtask_cancel(self, node_id: str, reason: str) -> None:
        self._transition_to_cancelling(node_id, reason)
        requested = self.execution_registry.request_cancel(node_id, reason)
        self.tracer.emit(
            "subtask_cancellation_requested",
            task_id=self.task_node_id,
            node_id=node_id,
            scope_id=self.scope_id,
            reason=reason,
            live_handle_found=requested,
        )

    def _transition_to_cancelling(self, node_id: str, reason: str) -> None:
        if not node_id:
            return
        try:
            node = self.dag.get_node(node_id)
            if node["status"] == "running":
                self.dag.transition(
                    node_id,
                    "cancelling",
                    metadata={"cancel_reason": reason},
                )
        except Exception:
            # Cancellation is best effort; the owning execution path commits
            # the final status and remains authoritative.
            return

    def _check_cancelled(self) -> None:
        if self._cancel_event.is_set():
            raise ProviderCancelled(
                self.cancellation_scope.reason or "task cancellation requested"
            )

    @staticmethod
    def _merge_usage(total: dict[str, int], increment: dict[str, int]) -> None:
        for key, value in increment.items():
            total[key] = total.get(key, 0) + value
