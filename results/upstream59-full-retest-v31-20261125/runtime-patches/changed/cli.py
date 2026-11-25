import argparse
import json
import os
import shlex
import sys
from pathlib import Path

from agent_runtime_demo.adaptive_routing import AdaptiveRoutingPolicy
from agent_runtime_demo.mcp import MCPClientManager, load_mcp_config
from agent_runtime_demo.inference_control import SGLangInferenceControl
from agent_runtime_demo.parallel_control import (
    HTTPGatewayResourceSnapshotProvider,
    NullResourceSnapshotProvider,
    ParallelControlConfig,
    TracerParallelTelemetry,
    build_parallel_controller,
)
from agent_runtime_demo.planning import InvalidTaskPlan, parse_task_plan
from agent_runtime_demo.providers import (
    DeterministicSmokeProvider,
    OpenAICompatibleProvider,
    OpenAIResponsesProvider,
    ProviderCancelled,
)
from agent_runtime_demo.planning import (
    ACCEPTANCE_POLICY_DESCRIPTION,
    FAILURE_POLICY_DESCRIPTION,
    JOIN_POLICY_DESCRIPTION,
)
from agent_runtime_demo.runtime import AgentRuntime
from agent_runtime_demo.speculation import (
    SmallActionPredictor,
    SpeculationConfig,
    SpeculationManager,
)
from agent_runtime_demo.tools import (
    ShellTool,
    ToolRegistry,
    build_workspace_tools,
    load_latency_benchmark_tools,
)
from agent_runtime_demo.tracing import JsonlTracer
from agent_runtime_demo.validation import (
    ArtifactValidator,
    CommandValidator,
    JSONSchemaValidator,
    ValidationRegistry,
)


NEUTRAL_SYSTEM_PROMPT_V1 = """
You are a software engineering agent operating in a restricted workspace.
Use the available structured tools to inspect and modify files. Use shell when a
structured tool is insufficient or when commands and tests must be executed.

## File Modification Rules (MANDATORY)

You MUST use the apply_patch tool for ALL code file modifications.
Do NOT use write_file, shell redirection, sed, or awk to modify existing code files.
apply_patch takes: path, old_text (the EXACT current content to replace), new_text (the replacement).
This ensures changes are made exactly where you intend, you see the diff,
and no accidental modifications are made to other parts of the file.
write_file is ONLY for creating entirely NEW files, never for editing existing ones.
Do not claim completion until relevant validation has passed.
Choose an execution structure only from the tools and Runtime control messages
available in the current turn.
When the task is complete, return a concise final answer without another tool call.
""".strip()


NEUTRAL_SYSTEM_PROMPT_V2 = """
You are a software engineering agent operating in a restricted workspace.
Use the available structured tools to inspect and modify files. Use shell when a
structured tool is insufficient or when commands and tests must be executed.
Do not claim completion until relevant validation has passed.
The Runtime supports parallel branches; use them when they materially help. It may
send a parallelization offer when it predicts benefit; treat the offer as advice,
not a command. If no offer is sent, independently choose serial or parallel execution.
No offer acknowledgement is required: ordinary tools and spawn_subtasks remain available.
An optional choose_execution_mode_v2 call can express a choice with its reason and,
for parallel execution, the plan. Do not issue two planning/decision calls in one turn.
When the task is complete, return a concise final answer without another tool call.
""".strip()


NEUTRAL_SYSTEM_PROMPT_V3 = """
You are a software engineering agent operating in a restricted workspace.
Use the available structured tools to inspect and modify files. Use shell when a
structured tool is insufficient or when commands and tests must be executed.
Do not claim completion until relevant validation has passed.
The Runtime supports parallel branches. When it sends a parallelization offer,
you must accept the offer and use parallel execution. If no offer is sent,
independently choose serial or parallel execution based on the task structure.
When the task is complete, return a concise final answer without another tool call.
""".strip()


NEUTRAL_SYSTEM_PROMPT_V4 = """
You are a software engineering agent operating in a restricted workspace.
Use the available structured tools to inspect and modify files. Use shell when a
structured tool is insufficient or when commands and tests must be executed.
Do not claim completion until relevant validation has passed.
The Runtime supports parallel branches. When it sends a parallelization offer,
you must accept the offer and use parallel execution. If no offer is sent,
independently choose serial or parallel execution based on the task structure.
Before creating subtasks, distinguish independent work from work whose concrete
inputs depend on an earlier tool call or result. Complete such prerequisites
first. After their results arrive, reevaluate the remaining work and create
parallel subtasks only for items that are then independent and fully specified.
When the task is complete, return a concise final answer without another tool call.
""".strip()


NEUTRAL_SYSTEM_PROMPT_V5 = """
You are a software engineering agent operating in a restricted workspace.
Use the available structured tools to inspect and modify files. Use shell when a
structured tool is insufficient or when commands and tests must be executed.
Do not claim completion until relevant validation has passed.

The Runtime can execute independent child work concurrently. When it sends a
RUNTIME_PARALLEL_OFFER_V2, you must answer before any ordinary tool with exactly
one choose_execution_mode_v2 call and copy its offer_id. The offer is advisory:
choose parallel, serial, or decline from the facts available at that boundary.

Evaluate only the immediate executable work frontier. Choose parallel only when
at least two substantial multi-step workstreams are executable now, have concrete
and already available inputs, and have disjoint writes. Otherwise choose serial
or decline and give a concrete reason. Work whose concrete inputs depend on an
earlier tool call, generated artifact, child result, or unresolved shared
interface is not on the current frontier. Complete those prerequisites first;
after their results arrive, reevaluate the remaining work and wait for a later
offer before planning a newly unlocked parallel wave.

A later fan-in does not make currently ready, disjoint producers serial. However,
do not package a post-fan-in consumer or any future-wave descendant into the
current plan. Every child in one accepted plan must be immediately executable and
independent of the other children in that plan, so its depends_on list must be
empty. The root joins children, integrates their results, reevaluates the next
frontier, and completes the full validator.

Never submit empty subtasks. Every child must declare exact owned files, focused
checks, and a completion_contract, and must call deliver_files as soon as its
checks pass. A child must not run the root validator or edit files outside its
ownership. Keep every subtasks[].task at most 512 characters. The task field
contains only the immediate objective and exceptional constraints that cannot be
recovered from referenced repository artifacts. Put authoritative repository
paths in input_refs and exact owned outputs plus trusted focused checks in
completion_contract. Do not copy long README text, test constants, expected
literals, inputs, or output examples into task.

When the task is complete, return a concise final answer without another tool call.
""".strip()


# Default neutral profile for new runs. Earlier versions remain immutable so
# recorded experiments can be reproduced from their profile and prompt digest.
NEUTRAL_SYSTEM_PROMPT = NEUTRAL_SYSTEM_PROMPT_V5


PARALLEL_AWARE_SYSTEM_PROMPT = f"""
You are a software engineering agent operating in a restricted workspace.
Use the available structured tools to inspect and modify files. Use shell when a
structured tool is insufficient or when commands and tests must be executed.
Do not claim completion until relevant validation has passed.
When a task contains two or more separable investigation or implementation
parts, call spawn_subtasks exactly once with the complete dependency plan so
ready child agents can run concurrently. Make every child objective
self-contained. Do not mix multiple spawn_subtasks calls in one model turn.
For spawn_subtasks failure_policy: {FAILURE_POLICY_DESCRIPTION}
For spawn_subtasks join_policy: {JOIN_POLICY_DESCRIPTION}
For spawn_subtasks acceptance_policy: {ACCEPTANCE_POLICY_DESCRIPTION}
When the task is complete, return a concise final answer without another tool call.
""".strip()


# The default is deliberately neutral so Initial-MLP experiments measure the
# effect of Runtime offers rather than a permanent parallelization instruction.
SYSTEM_PROMPT = NEUTRAL_SYSTEM_PROMPT


def load_trace_checkpoint(
    trace_path: Path,
    *,
    system_prompt: str,
    task: str,
    before_step: int,
) -> tuple[list[dict], int]:
    """Rebuild a protocol-complete root conversation before one trace step.

    This is a semantic checkpoint: it restores model/tool messages but creates a
    fresh Runtime DAG.  Filesystem state must be restored separately by the
    harness.  Only completed root assistant/tool pairs are inherited; predictor
    and Runtime telemetry are recomputed.  A materialized checkpoint may append
    one ``semantic_checkpoint_state`` event containing the verified compact
    state that replaces omitted bulky write calls.
    """
    if before_step <= 0:
        raise ValueError("before_step must be greater than zero")
    messages: list[dict] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": task},
    ]
    included_step = 0
    pending_tool_ids: set[str] = set()
    with trace_path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"invalid trace JSON at line {line_number}: {exc}"
                ) from exc
            if row.get("scope_id") != "root":
                continue
            step = row.get("step")
            if not isinstance(step, int) or step >= before_step:
                continue
            event = row.get("event")
            if event == "model_response":
                message: dict = {
                    "role": "assistant",
                    "content": row.get("content") or "",
                }
                tool_calls = []
                for raw_call in row.get("tool_calls") or []:
                    call_id = str(raw_call.get("id") or "")
                    name = str(raw_call.get("name") or "")
                    arguments = raw_call.get("arguments")
                    if not call_id or not name or not isinstance(arguments, dict):
                        raise ValueError(
                            f"invalid tool call in trace line {line_number}"
                        )
                    pending_tool_ids.add(call_id)
                    tool_calls.append(
                        {
                            "id": call_id,
                            "type": "function",
                            "function": {
                                "name": name,
                                "arguments": json.dumps(
                                    arguments, ensure_ascii=False, separators=(",", ":")
                                ),
                            },
                        }
                    )
                if tool_calls:
                    message["tool_calls"] = tool_calls
                messages.append(message)
                included_step = max(included_step, step)
            elif event == "tool_result":
                call_id = str(row.get("tool_call_id") or "")
                name = str(row.get("tool") or "")
                if call_id not in pending_tool_ids:
                    raise ValueError(
                        f"orphan root tool result in trace line {line_number}: {call_id}"
                    )
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call_id,
                        "name": name,
                        "content": json.dumps(
                            row.get("result"), ensure_ascii=False, separators=(",", ":")
                        ),
                    }
                )
                pending_tool_ids.remove(call_id)
            elif event == "semantic_checkpoint_state":
                content = row.get("content")
                if not isinstance(content, str) or not content.strip():
                    raise ValueError(
                        "semantic checkpoint state must contain non-empty content "
                        f"at line {line_number}"
                    )
                if pending_tool_ids:
                    raise ValueError(
                        "semantic checkpoint state appears before tool results at "
                        f"line {line_number}"
                    )
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "[Runtime verified recovery checkpoint]\n" + content.strip()
                        ),
                    }
                )
                included_step = max(included_step, step)
    if pending_tool_ids:
        raise ValueError(
            "trace checkpoint ends with unmatched tool calls: "
            + ", ".join(sorted(pending_tool_ids))
        )
    if included_step == 0:
        raise ValueError("trace contains no completed root model turn before checkpoint")
    return messages, included_step


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Minimal agent runtime demo")
    parser.add_argument("task", help="Task for the agent")
    parser.add_argument(
        "--system-prompt-profile",
        choices=("neutral", "parallel-aware"),
        default=os.getenv("AGENT_SYSTEM_PROMPT_PROFILE", "neutral"),
        help=(
            "System-prompt policy. neutral is the benchmark default; "
            "parallel-aware is retained only for an explicit-prompt ablation."
        ),
    )
    parser.add_argument(
        "--provider",
        choices=("openai-compatible", "deterministic-smoke"),
        default="openai-compatible",
    )
    parser.add_argument("--base-url", default=os.getenv("MODEL_BASE_URL", "http://127.0.0.1:8000/v1"))
    parser.add_argument("--model", default=os.getenv("MODEL_NAME", "agent-auto"))
    parser.add_argument(
        "--adaptive-model-escalation",
        action="store_true",
        default=os.getenv("AGENT_ADAPTIVE_MODEL_ESCALATION", "").lower()
        in {"1", "true", "yes", "on"},
        help="Escalate repeated weak-model validation failures to a strong model",
    )
    parser.add_argument(
        "--weak-model",
        default=os.getenv("AGENT_WEAK_MODEL", "Qwen3-4B"),
    )
    parser.add_argument(
        "--strong-model",
        default=os.getenv("AGENT_STRONG_MODEL", "Qwen3-8B"),
    )
    parser.add_argument(
        "--criticality-action",
        choices=("strong_model", "thinking"),
        default=os.getenv("AGENT_CRITICALITY_ACTION", "strong_model"),
        help=(
            "After the weak-model failure threshold, either retry on the strong "
            "model or keep the weak model and enable thinking"
        ),
    )
    parser.add_argument(
        "--weak-validation-failures",
        type=int,
        default=int(os.getenv("AGENT_WEAK_VALIDATION_FAILURES", "2")),
        help="Weak-model validation failures before require_strong routing",
    )
    parser.add_argument(
        "--critical-path-failures",
        type=int,
        default=int(os.getenv("AGENT_CRITICAL_PATH_FAILURES", "1")),
        help="Weak-model failures before escalating an all_terminal join blocker",
    )
    parser.add_argument(
        "--max-branch-attempts",
        type=int,
        default=int(os.getenv("AGENT_MAX_BRANCH_ATTEMPTS", "2")),
        help="Maximum whole-child attempts including the initial weak attempt",
    )
    parser.add_argument("--api-key", default=os.getenv("MODEL_API_KEY", ""))
    parser.add_argument(
        "--wire-api",
        choices=("chat-completions", "responses"),
        default=os.getenv("MODEL_WIRE_API", "chat-completions"),
        help="OpenAI-compatible wire API used by the model provider",
    )
    parser.add_argument(
        "--responses-compat",
        choices=("openai", "vsr-0.3"),
        default=os.getenv("RESPONSES_COMPAT", "openai"),
        help="Responses tool-loop compatibility mode",
    )
    parser.add_argument(
        "--reasoning-mode",
        choices=("auto", "off", "on"),
        default=os.getenv("AGENT_RUNTIME_REASONING_MODE", "off"),
        help=(
            "Per-request reasoning policy. Experiments default to 'off'; 'on' "
            "or 'auto' must be an explicit non-benchmark override. With VSR "
            "v0.3, 'on' selects the Qwen3 reasoning route without globally "
            "changing worker defaults."
        ),
    )
    parser.add_argument(
        "--stream",
        action="store_true",
        help="Stream Responses API text and tool-call events over SSE",
    )
    parser.add_argument("--workspace", type=Path, default=Path(os.getenv("AGENT_WORKSPACE", ".")))
    parser.add_argument("--max-steps", type=int, default=20)
    parser.add_argument(
        "--max-parallelism",
        type=int,
        default=20,
        help="Maximum concurrent child agents and tool workers per scheduling level",
    )
    parser.add_argument("--max-subtasks", type=int, default=20)
    parser.add_argument("--require-file-branch-contract", action="store_true",
                        help="Require explicit output files and verification targets for every coding branch")
    parser.add_argument(
        "--parallel-control",
        choices=("off", "shadow", "active"),
        default=os.getenv("AGENT_PARALLEL_CONTROL", "off"),
        help=(
            "Optional parallel control plane. off preserves the base runtime; "
            "shadow records decisions without changing execution; active may issue "
            "a structured root-recovery offer when a configured predictor approves it."
        ),
    )
    parser.add_argument(
        "--parallel-resource-summary-url",
        default=os.getenv("AGENT_PARALLEL_RESOURCE_SUMMARY_URL", ""),
        help=(
            "Optional read-only Gateway JSON summary used only as parallel-control "
            "features; failures never block task execution"
        ),
    )
    parser.add_argument(
        "--parallel-classifier",
        type=Path,
        default=(
            Path(os.environ["AGENT_PARALLEL_CLASSIFIER"])
            if os.getenv("AGENT_PARALLEL_CLASSIFIER")
            else None
        ),
        help="Versioned local JSON classifier artifact for shadow or active mode",
    )
    parser.add_argument(
        "--parallel-branch-local",
        action="store_true",
        help=(
            "Allow active mode to offer one append-only local recovery DAG after "
            "a join-critical branch rejection"
        ),
    )
    parser.add_argument(
        "--parallel-resource-timeout",
        type=float,
        default=0.2,
        help="Timeout in seconds for the optional resource summary read",
    )
    parser.add_argument(
        "--max-subtask-depth",
        type=int,
        default=1,
        help="Maximum child-agent delegation depth; 1 allows root to spawn one level",
    )
    parser.add_argument(
        "--no-subtasks",
        action="store_true",
        help="Do not expose the spawn_subtasks runtime control tool",
    )
    parser.add_argument(
        "--plan-file",
        type=Path,
        help="Inject a deterministic spawn_subtasks JSON plan before model synthesis",
    )
    parser.add_argument("--tool-timeout", type=int, default=30)
    parser.add_argument(
        "--latency-benchmark-config",
        type=Path,
        help="Opt-in controlled read-only latency tools for speculation experiments",
    )
    parser.add_argument(
        "--mcp-config",
        type=Path,
        help="JSON file containing stdio MCP server definitions",
    )
    parser.add_argument(
        "--mcp-only",
        action="store_true",
        help="Expose only dynamically discovered MCP tools to the model",
    )
    parser.add_argument("--trace-path", type=Path)
    parser.add_argument(
        "--resume-trace",
        type=Path,
        help=(
            "Rebuild root assistant/tool history from a prior JSONL trace. "
            "This creates a fresh DAG and is not an in-place container resume."
        ),
    )
    parser.add_argument(
        "--resume-before-step",
        type=int,
        help="Exclude this and later prior trace steps from the semantic checkpoint",
    )
    parser.add_argument(
        "--resume-overlay-trace",
        type=Path,
        help=(
            "Append completed root turns from a later semantic-resume trace after "
            "the base --resume-trace history"
        ),
    )
    parser.add_argument(
        "--resume-overlay-before-step",
        type=int,
        help="Exclude this and later steps from --resume-overlay-trace",
    )
    parser.add_argument(
        "--execution-state-log",
        type=Path,
        help="Write compact Runtime execution-state observations as JSONL",
    )
    parser.add_argument(
        "--codex-shadow-predictor",
        action="store_true",
        help="Record Codex-simulated Action/Width/Workload without affecting execution",
    )
    parser.add_argument(
        "--codex-shadow-workload",
        choices=("easy", "medium", "hard"),
        default="medium",
        help="Explicit workload profile for the shadow Workload head",
    )
    parser.add_argument(
        "--dag-path",
        type=Path,
        help="Write the final execution DAG JSON; defaults next to --trace-path",
    )
    parser.add_argument("--validation-command", default="")
    parser.add_argument(
        "--acceptance-command",
        action="append",
        default=[],
        metavar="REF=COMMAND",
        help="Register a trusted child-candidate command validator (shell is not used)",
    )
    parser.add_argument(
        "--acceptance-schema",
        action="append",
        default=[],
        metavar="REF=JSON_SCHEMA_PATH",
        help="Register a JSON Schema validator for child candidate text",
    )
    parser.add_argument(
        "--acceptance-artifact",
        action="append",
        default=[],
        metavar="REF=PATH[,PATH...]",
        help="Register required workspace files for child candidate acceptance",
    )
    parser.add_argument("--quiet-trace", action="store_true")
    parser.add_argument(
        "--sglang-worker-url",
        action="append",
        default=[],
        help=(
            "Direct SGLang worker URL used for loser abort and session-KV release; "
            "repeat for every worker in the gateway pool"
        ),
    )
    parser.add_argument(
        "--sglang-worker-model",
        action="append",
        default=[],
        metavar="URL=MODEL",
        help=(
            "Authoritative physical model identity for a worker selected behind a "
            "logical VSR alias; repeat for every worker"
        ),
    )
    parser.add_argument(
        "--sglang-control-timeout",
        type=float,
        default=5.0,
        help="Timeout in seconds for each SGLang abort/close_session control request",
    )
    parser.add_argument(
        "--sglang-gateway-url",
        default=os.getenv("SGLANG_GATEWAY_URL", ""),
        help="Gateway control URL used to invalidate cache-aware shadow prefixes",
    )
    parser.add_argument(
        "--sglang-gateway-model",
        default=os.getenv("SGLANG_GATEWAY_MODEL", ""),
        help="Physical model id owning the gateway cache-aware tree",
    )
    parser.add_argument(
        "--sglang-abort-settle-seconds",
        type=float,
        default=0.5,
        help=(
            "Delay between abort acknowledgement and close_session so the worker "
            "can drop the running request's KV lock"
        ),
    )
    parser.add_argument(
        "--sglang-close-retry-count",
        type=int,
        default=1,
        help="Number of close_session attempts after abort",
    )
    parser.add_argument(
        "--speculation-mode",
        choices=("off", "shadow", "readonly"),
        default=os.getenv("AGENT_SPECULATION_MODE", "off"),
        help=(
            "Optional pluggable speculation path: shadow only scores predictions; "
            "readonly also pre-executes locally trusted read-only tools"
        ),
    )
    parser.add_argument(
        "--speculation-model",
        type=Path,
        default=Path(os.environ["AGENT_SPECULATION_MODEL"])
        if os.getenv("AGENT_SPECULATION_MODEL")
        else None,
        help="JSON CPU classifier produced by scripts/train_speculation_classifier.py",
    )
    parser.add_argument(
        "--speculation-confidence",
        type=float,
        default=float(os.getenv("AGENT_SPECULATION_CONFIDENCE", "0.35")),
    )
    parser.add_argument(
        "--speculation-top-k",
        type=int,
        default=int(os.getenv("AGENT_SPECULATION_TOP_K", "3")),
    )
    parser.add_argument(
        "--speculation-max-workers",
        type=int,
        default=int(os.getenv("AGENT_SPECULATION_MAX_WORKERS", "4")),
        help="Maximum speculative Tool executions across concurrent branches",
    )
    parser.add_argument(
        "--speculation-readonly-tool",
        action="append",
        default=[],
        help=(
            "Explicitly trust an audited external tool for read-only speculation. "
            "Native read_file/list_files/search_text opt in without this flag."
        ),
    )
    parser.add_argument(
        "--speculation-overlay-path",
        type=Path,
        help="Write speculative DAG overlays and commit/discard outcomes to JSON",
    )
    return parser


def main() -> None:
    parser = build_parser()
    parser.add_argument("--parallel-v2", choices=("off", "shadow", "active"), default="off")
    parser.add_argument("--parallel-v2-mock", type=Path, help="Explicit mock predictor rules JSON; not a trained MLP")
    parser.add_argument("--parallel-v2-heads-mock", type=Path, help="Three probability-head fixture using unified input; no trained model")
    parser.add_argument("--parallel-v2-resource-score", type=float, default=1.0)
    parser.add_argument("--parallel-v2-max-expansions", type=int, default=4)
    args = parser.parse_args()
    if args.codex_shadow_predictor and args.execution_state_log is None:
        parser.error("--codex-shadow-predictor requires --execution-state-log")
    if args.stream and args.wire_api != "responses":
        parser.error("--stream currently requires --wire-api responses")
    if args.mcp_only and not args.mcp_config:
        parser.error("--mcp-only requires --mcp-config")
    if args.no_subtasks and args.plan_file:
        parser.error("--plan-file cannot be combined with --no-subtasks")
    if args.parallel_branch_local and args.parallel_control != "active":
        parser.error("--parallel-branch-local requires --parallel-control active")
    if args.speculation_mode != "off" and args.speculation_model is None:
        parser.error("--speculation-model is required when speculation is enabled")
    if (args.resume_trace is None) != (args.resume_before_step is None):
        parser.error("--resume-trace and --resume-before-step must be provided together")
    if (args.resume_overlay_trace is None) != (args.resume_overlay_before_step is None):
        parser.error(
            "--resume-overlay-trace and --resume-overlay-before-step must be provided together"
        )
    if args.resume_overlay_trace is not None and args.resume_trace is None:
        parser.error("--resume-overlay-trace requires --resume-trace")
    initial_plan = None
    if args.plan_file:
        try:
            initial_plan = parse_task_plan(
                json.loads(args.plan_file.read_text(encoding="utf-8")),
                max_subtasks=args.max_subtasks,
            )
        except (OSError, json.JSONDecodeError, InvalidTaskPlan) as exc:
            parser.error(f"invalid --plan-file: {exc}")
    shell = ShellTool(args.workspace, timeout_seconds=args.tool_timeout)
    native_tools = [] if args.mcp_only else [shell, *build_workspace_tools(args.workspace)]
    if args.latency_benchmark_config:
        try:
            native_tools.extend(load_latency_benchmark_tools(args.latency_benchmark_config))
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            parser.error(f"invalid --latency-benchmark-config: {exc}")
    closers = []
    if args.mcp_config:
        manager = MCPClientManager(
            load_mcp_config(args.mcp_config, args.workspace),
            timeout_seconds=args.tool_timeout,
        )
        native_tools.extend(manager.connect())
        closers.append(manager.close)
    tools = ToolRegistry(native_tools, closers=closers)
    tracer = JsonlTracer(args.trace_path, echo=not args.quiet_trace)
    parallel_config = ParallelControlConfig(
        mode=args.parallel_control,
        classifier_path=(str(args.parallel_classifier) if args.parallel_classifier else ""),
        enable_branch_local_expansion=args.parallel_branch_local,
    )
    from agent_runtime_demo.parallel_control_v2 import ConfigV2, ControllerV2, MockPredictorV2
    try:
        from agent_runtime_demo.classifier_adapter_v2 import ThreeHeadAdapterV2, MockThreeHeadsV2
        from agent_runtime_demo.classifier_input_v2 import INPUT_VERSION
        if args.parallel_v2_mock and args.parallel_v2_heads_mock:
            raise ValueError("choose legacy mock or three-head mock, not both")
        v2_fixture = json.loads(args.parallel_v2_mock.read_text(encoding="utf-8")) if args.parallel_v2_mock else None
        predictor_v2 = MockPredictorV2(**v2_fixture) if v2_fixture is not None else None
        if args.parallel_v2_heads_mock:
            fixture = json.loads(args.parallel_v2_heads_mock.read_text(encoding="utf-8"))
            predictor_v2 = ThreeHeadAdapterV2(MockThreeHeadsV2(**fixture),
                model_version="mock-three-heads-v2.1", input_version=INPUT_VERSION)
        v2_controller = ControllerV2(
            ConfigV2(mode=args.parallel_v2, resource_score=args.parallel_v2_resource_score,
                     max_expansions=args.parallel_v2_max_expansions),
            predictor_v2)
        if args.parallel_v2 == "active" and args.parallel_control == "active":
            raise ValueError("v2 active cannot compete with active v1 controller")
    except (OSError, ValueError, TypeError) as exc:
        parser.error(f"invalid v2 configuration: {exc}")
    try:
        parallel_controller = build_parallel_controller(
            parallel_config,
            telemetry=TracerParallelTelemetry(tracer),
        )
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        parser.error(str(exc))
    if args.parallel_resource_summary_url:
        resource_snapshot_provider = HTTPGatewayResourceSnapshotProvider(
            args.parallel_resource_summary_url,
            timeout_seconds=args.parallel_resource_timeout,
        )
    else:
        resource_snapshot_provider = NullResourceSnapshotProvider()
    speculation_manager = None
    if args.speculation_mode != "off":
        overlay_path = args.speculation_overlay_path
        if overlay_path is None and args.trace_path is not None:
            overlay_path = args.trace_path.with_name(
                args.trace_path.stem + ".speculation.json"
            )
        try:
            predictor = SmallActionPredictor.load(args.speculation_model)
            speculation_manager = SpeculationManager(
                predictor,
                tools,
                tracer,
                SpeculationConfig(
                    mode=args.speculation_mode,
                    confidence_threshold=args.speculation_confidence,
                    top_k=args.speculation_top_k,
                    max_workers=args.speculation_max_workers,
                    trusted_readonly_tools=frozenset(args.speculation_readonly_tool),
                    overlay_path=overlay_path,
                ),
            )
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            parser.error(f"invalid speculation configuration: {exc}")
    configured_worker_urls = list(args.sglang_worker_url)
    if not configured_worker_urls:
        configured_worker_urls = [
            item.strip()
            for item in os.getenv("SGLANG_WORKER_URLS", "").split(",")
            if item.strip()
        ]
    inference_control = None
    if configured_worker_urls:
        worker_model_map = {}
        try:
            for item in args.sglang_worker_model:
                worker_url, model = item.rsplit("=", 1)
                if not worker_url.strip() or not model.strip():
                    raise ValueError(item)
                worker_model_map[worker_url.strip().rstrip("/")] = model.strip()
        except ValueError as exc:
            parser.error(f"invalid --sglang-worker-model URL=MODEL: {exc}")
        inference_control = SGLangInferenceControl(
            configured_worker_urls,
            gateway_url=args.sglang_gateway_url,
            gateway_model=args.sglang_gateway_model,
            worker_model_map=worker_model_map,
            timeout_seconds=args.sglang_control_timeout,
            abort_settle_seconds=args.sglang_abort_settle_seconds,
            close_retry_count=args.sglang_close_retry_count,
            event_handler=lambda event, payload: tracer.emit(event, **payload),
        )
    dag_path = args.dag_path
    if dag_path is None and args.trace_path is not None:
        dag_path = args.trace_path.with_name(args.trace_path.stem + ".dag.json")
    streamed_text = False

    def handle_stream_event(event: dict) -> None:
        nonlocal streamed_text
        payload = dict(event)
        stream_type = payload.pop("type", "unknown")
        tracer.emit("provider_stream_event", stream_type=stream_type, **payload)
        if stream_type == "text_delta":
            streamed_text = True
            print(event.get("delta", ""), end="", flush=True)

    if args.provider == "deterministic-smoke":
        provider = DeterministicSmokeProvider()
    elif args.wire_api == "responses":
        provider = OpenAIResponsesProvider(
            args.base_url,
            args.model,
            args.api_key,
            compatibility=args.responses_compat,
            stream=args.stream,
            stream_event_handler=handle_stream_event if args.stream else None,
        )
    else:
        provider = OpenAICompatibleProvider(args.base_url, args.model, args.api_key)

    validator = None
    if args.validation_command:
        def validate() -> tuple[bool, str]:
            result = shell.execute({"command": args.validation_command})
            return bool(result.get("ok")), json.dumps(result, ensure_ascii=False)

        validator = validate

    validation_registry = ValidationRegistry()
    try:
        for item in args.acceptance_command:
            ref, command = item.split("=", 1)
            validation_registry.register(
                ref,
                CommandValidator(ref, tuple(shlex.split(command)), args.workspace),
            )
        for item in args.acceptance_schema:
            ref, schema_path = item.split("=", 1)
            schema = json.loads(Path(schema_path).read_text(encoding="utf-8"))
            validation_registry.register(ref, JSONSchemaValidator(ref, schema))
        for item in args.acceptance_artifact:
            ref, raw_paths = item.split("=", 1)
            paths = [path.strip() for path in raw_paths.split(",") if path.strip()]
            validation_registry.register(
                ref,
                ArtifactValidator(ref, paths, args.workspace),
            )
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        parser.error(f"invalid acceptance validator: {exc}")

    selected_system_prompt = (
        NEUTRAL_SYSTEM_PROMPT
        if args.system_prompt_profile == "neutral"
        else PARALLEL_AWARE_SYSTEM_PROMPT
    )
    runtime = AgentRuntime(
        require_file_branch_contract=args.require_file_branch_contract,
        provider=provider,
        tools=tools,
        system_prompt=selected_system_prompt,
        max_steps=args.max_steps,
        validator=validator,
        tracer=tracer,
        dag_path=dag_path,
        max_parallelism=args.max_parallelism,
        max_subtasks=args.max_subtasks,
        max_subtask_depth=args.max_subtask_depth,
        max_plan_expansions=(
            args.parallel_v2_max_expansions if args.parallel_v2 == "active" else
            1 + parallel_config.max_local_expansions
            if parallel_config.mode == "active"
            else 1
        ),
        allow_subtasks=not args.no_subtasks,
        initial_plan=initial_plan,
        inference_control=inference_control,
        validation_registry=validation_registry,
        validation_workspace=args.workspace,
        speculation_manager=speculation_manager,
        adaptive_routing_policy=AdaptiveRoutingPolicy(
            enabled=args.adaptive_model_escalation,
            weak_model=args.weak_model,
            strong_model=args.strong_model,
            weak_validation_failure_threshold=args.weak_validation_failures,
            critical_path_failure_threshold=args.critical_path_failures,
            max_branch_attempts=args.max_branch_attempts,
            escalation_action=args.criticality_action,
        ),
        parallel_controller=parallel_controller,
        parallel_controller_v2=v2_controller,
        resource_snapshot_provider=resource_snapshot_provider,
        initial_reasoning_mode=args.reasoning_mode,
        execution_state_log_path=args.execution_state_log,
        codex_shadow_predictor=args.codex_shadow_predictor,
        codex_shadow_workload=args.codex_shadow_workload,
    )
    initial_messages = None
    initial_step = 0
    if args.resume_trace is not None:
        try:
            initial_messages, initial_step = load_trace_checkpoint(
                args.resume_trace,
                system_prompt=selected_system_prompt,
                task=args.task,
                before_step=args.resume_before_step,
            )
            overlay_message_count = 0
            if args.resume_overlay_trace is not None:
                overlay_messages, overlay_step = load_trace_checkpoint(
                    args.resume_overlay_trace,
                    system_prompt=selected_system_prompt,
                    task=args.task,
                    before_step=args.resume_overlay_before_step,
                )
                # The overlay begins with its own system/task prefix because it
                # came from a fresh Harbor run. Keep the base prefix exactly once.
                initial_messages.extend(overlay_messages[2:])
                overlay_message_count = len(overlay_messages) - 2
                initial_step = max(initial_step, overlay_step)
        except (OSError, ValueError) as exc:
            parser.error(f"invalid resume checkpoint: {exc}")
        tracer.emit(
            "semantic_checkpoint_loaded",
            source_trace=str(args.resume_trace),
            before_step=args.resume_before_step,
            restored_step=initial_step,
            inherited_message_count=len(initial_messages),
            overlay_trace=(
                str(args.resume_overlay_trace)
                if args.resume_overlay_trace is not None
                else None
            ),
            overlay_before_step=args.resume_overlay_before_step,
            overlay_message_count=overlay_message_count,
        )
    try:
        final_answer = runtime.run(
            args.task,
            initial_messages=initial_messages,
            initial_step=initial_step,
        )
    except ProviderCancelled:
        print("\nTask cancelled.", file=sys.stderr)
        raise SystemExit(130)
    if args.stream and streamed_text:
        print()
    else:
        print(final_answer)


if __name__ == "__main__":
    main()
