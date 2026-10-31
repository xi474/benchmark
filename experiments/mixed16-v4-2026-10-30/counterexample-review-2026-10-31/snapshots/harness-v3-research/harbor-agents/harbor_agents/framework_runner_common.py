"""Shared runtime helpers for the LangGraph and Strands Harbor runners."""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Any

try:
    from unified_telemetry import UnifiedEventWriter, read_events
    from model_throughput import analyze_model_throughput, write_model_throughput_artifacts
except ImportError:  # local source-tree execution
    from harbor_agents.unified_telemetry import UnifiedEventWriter, read_events
    from harbor_agents.model_throughput import analyze_model_throughput, write_model_throughput_artifacts


TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "exec",
            "description": "Run a shell command in the task workspace and return output plus exit code.",
            "parameters": {
                "type": "object",
                "properties": {"command": {"type": "string"}},
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a UTF-8 file relative to the task workspace.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write complete UTF-8 content to a workspace file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "Replace one exact unique text occurrence in a workspace file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "old_text": {"type": "string"},
                    "new_text": {"type": "string"},
                },
                "required": ["path", "old_text", "new_text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_dir",
            "description": "List a directory relative to the workspace.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string", "default": "."}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_files",
            "description": "Find workspace files matching a glob pattern.",
            "parameters": {
                "type": "object",
                "properties": {"pattern": {"type": "string"}},
                "required": ["pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "grep",
            "description": "Search workspace file contents with a regex or literal pattern.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string"},
                    "glob_pattern": {"type": "string", "default": "**/*"},
                },
                "required": ["pattern"],
            },
        },
    },
]


SYSTEM_PROMPT = """You are an autonomous software and data-engineering agent running in /app.
Solve the user's task by inspecting and modifying the workspace with the available tools.
Do not merely explain a solution: create the requested files and run relevant checks.
All paths must remain inside /app. Continue until the task is complete, then give a concise final response.
"""


class NoopWriter:
    """Tool sink used when the framework's native hooks own tool telemetry."""

    def emit(self, _event_type: str, **_kwargs: Any) -> str:
        return f"noop-{uuid.uuid4().hex}"


def make_writer(harness: str, model: str) -> tuple[UnifiedEventWriter, Path, Path]:
    telemetry_dir = Path(os.environ.get("HARNESS_TELEMETRY_DIR", "/logs/agent/telemetry"))
    telemetry_dir.mkdir(parents=True, exist_ok=True)
    trial_id = os.environ.get("HARNESS_TRIAL_ID") or f"{harness}-{uuid.uuid4().hex[:8]}"
    task_id = os.environ.get("HARNESS_TASK_ID") or "unknown-task"
    events_path = telemetry_dir / "events-v2.jsonl"
    writer = UnifiedEventWriter(
        events_path,
        run_id=trial_id,
        trial_id=trial_id,
        task_id=task_id,
        agent_id=f"{harness}-root",
        harness=harness,
        model=model,
        execution_mode="real",
        source="agent-native" if harness == "strands" else "adapter",
        synthetic=False,
    )
    return writer, telemetry_dir, events_path


def write_harbor_summary(
    telemetry_dir: Path,
    events_path: Path,
    workflow_summary: dict[str, Any],
    *,
    harness: str,
) -> dict[str, Any]:
    events = read_events(events_path)
    throughput = analyze_model_throughput(events)
    write_model_throughput_artifacts(telemetry_dir / "model-throughput", throughput)
    throughput_summary = throughput["summary"]
    planning = workflow_summary.get("planning") or {}
    topology = workflow_summary.get("agent_topology") or {}
    capabilities = workflow_summary.get("capabilities") or {}
    terminal_workflow = next(
        (event for event in reversed(events) if event.get("event_type") == "workflow.completed"),
        {},
    )
    summary = {
        "schema_version": 2,
        "observability_level": "L2-native",
        "harness": harness,
        "orchestration_status": terminal_workflow.get("status") or "not_observed",
        "orchestration_reason": terminal_workflow.get("reason"),
        # Missing provider usage is unknown, not a measured zero.  Reuse the
        # canonical analyzer so the top-level and detailed summaries agree.
        "n_input_tokens": throughput_summary.get("input_tokens"),
        "n_output_tokens": throughput_summary.get("output_tokens"),
        "n_cache_tokens": throughput_summary.get("cache_tokens"),
        "token_usage_status": (
            "unavailable"
            if throughput_summary.get("token_aggregation_level") == "not-observed"
            else "observed"
        ),
        "cost_usd": None,
        "events_path": "agent/telemetry/events-v2.jsonl",
        "events_v2_path": "agent/telemetry/events-v2.jsonl",
        "workflow_dir": "agent/telemetry/workflow",
        "execution_dag_path": "agent/telemetry/workflow/execution-dag.json",
        "planning_analysis_path": "agent/telemetry/workflow/workflow-summary.json",
        "planning_level": planning.get("planning_level"),
        "plan_source": planning.get("plan_source"),
        "subagent_capability_available": capabilities.get("subagent_capability_available"),
        "subagent_count": topology.get("subagent_count", capabilities.get("subagent_count")),
        "autonomous_delegation": capabilities.get("autonomous_delegation"),
        "reason_if_not_observed": planning.get("reason_if_not_observed"),
        "resource_scope": "task-container",
        "resource_samples": 0,
        "event_count": len(events),
        "model_throughput_path": "agent/telemetry/model-throughput.json",
        "model_throughput": throughput["summary"],
    }
    (telemetry_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return summary
