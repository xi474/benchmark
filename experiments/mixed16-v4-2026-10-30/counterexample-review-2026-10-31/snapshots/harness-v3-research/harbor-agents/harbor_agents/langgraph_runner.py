#!/usr/bin/env python3
"""Run one Harbor task through a real LangGraph control loop."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import uuid
from pathlib import Path
from typing import Any, TypedDict

try:
    from agent_tools import make_tools
    from framework_runner_common import SYSTEM_PROMPT, TOOL_SCHEMAS, make_writer, write_harbor_summary
    from langgraph_planner import (
        MAX_TASKS,
        Plan,
        PlanTask,
        parse_plan,
        planner_messages,
        topological_waves,
        validate_plan,
    )
except ImportError:  # local source-tree execution
    from harbor_agents.agent_tools import make_tools
    from harbor_agents.framework_runner_common import (
        SYSTEM_PROMPT,
        TOOL_SCHEMAS,
        make_writer,
        write_harbor_summary,
    )
    from harbor_agents.langgraph_planner import (
        MAX_TASKS,
        Plan,
        PlanTask,
        parse_plan,
        planner_messages,
        topological_waves,
        validate_plan,
    )
from langgraph.graph import END, START, StateGraph
try:
    from langgraph_adapter import LangGraphTelemetryAdapter
except ImportError:  # local source-tree execution
    from harbor_agents.adapters.langgraph_adapter import LangGraphTelemetryAdapter
from openai import AsyncOpenAI


class AgentState(TypedDict, total=False):
    messages: list[dict[str, Any]]
    pending_calls: list[dict[str, Any]]
    iterations: int
    plan: dict[str, Any] | None
    subtask_results: list[dict[str, Any]]
    final_answer: str


def usage_payload(usage: Any) -> dict[str, Any] | None:
    if usage is None:
        return None
    prompt = int(getattr(usage, "prompt_tokens", 0) or 0)
    completion = int(getattr(usage, "completion_tokens", 0) or 0)
    details = getattr(usage, "prompt_tokens_details", None)
    return {
        "input_tokens": prompt,
        "output_tokens": completion,
        "cache_tokens": int(getattr(details, "cached_tokens", 0) or 0) if details else 0,
        "total_tokens": prompt + completion,
        "source": "openai-compatible-response",
        "synthetic": False,
    }


async def run(args: argparse.Namespace) -> int:
    instruction = args.instruction_file.read_text(encoding="utf-8")
    writer, telemetry_dir, events_path = make_writer("langgraph", args.model)
    tools = make_tools(writer, Path(args.workspace))
    tools_by_name = {tool.__name__: tool for tool in tools}
    client = AsyncOpenAI(
        api_key=os.environ["HARNESS_API_KEY"],
        base_url=os.environ.get("HARNESS_BASE_URL") or "https://api.openai.com/v1",
    )
    model_extra = (
        {"chat_template_kwargs": {"enable_thinking": False}}
        if os.environ.get("HARNESS_LANGGRAPH_DISABLE_THINKING", "0") == "1"
        else None
    )

    async def call_model(
        messages: list[dict[str, Any]],
        *,
        agent_id: str,
        node_id: str,
        tools: list[dict[str, Any]] | None,
        max_tokens: int,
    ) -> Any:
        request_id = f"langgraph-model-{uuid.uuid4().hex[:12]}"
        writer.emit(
            "model.request",
            agent_id=agent_id,
            workflow_id="langgraph-harbor-loop",
            node_id=node_id,
            model=args.model,
            status="started",
            model_request_id=request_id,
            payload={"message_count": len(messages), "tool_count": len(tools or [])},
        )
        try:
            response = await client.chat.completions.create(
                model=args.model,
                messages=messages,
                tools=tools or None,
                tool_choice="auto" if tools else None,
                temperature=0,
                max_tokens=max_tokens,
                extra_body=model_extra,
            )
        except Exception as exc:
            writer.emit(
                "model.response",
                agent_id=agent_id,
                workflow_id="langgraph-harbor-loop",
                node_id=node_id,
                model=args.model,
                status="failed",
                error=str(exc),
                model_request_id=request_id,
                payload={"error_type": type(exc).__name__},
            )
            raise
        writer.emit(
            "model.response",
            agent_id=agent_id,
            workflow_id="langgraph-harbor-loop",
            node_id=node_id,
            model=args.model,
            status="completed",
            model_request_id=request_id,
            token_usage=usage_payload(response.usage),
            payload={
                "finish_reason": response.choices[0].finish_reason,
                "tool_call_count": len(response.choices[0].message.tool_calls or []),
            },
        )
        return response

    async def run_worker(task: PlanTask, dependencies: dict[str, str]) -> dict[str, Any]:
        worker_id = f"langgraph-worker-{task.id}"
        writer.emit(
            "agent.created",
            agent_id=worker_id,
            parent_agent_id="langgraph-root",
            workflow_id="langgraph-harbor-loop",
            node_id=f"worker-{task.id}",
            agent_role="worker",
            payload={
                "objective": task.objective,
                "depends_on": list(task.depends_on),
                "write_scope": list(task.write_scope),
                "parallel_group": task.parallel_group,
            },
        )
        writer.emit(
            "agent.run.started",
            agent_id=worker_id,
            parent_agent_id="langgraph-root",
            workflow_id="langgraph-harbor-loop",
            node_id=f"worker-{task.id}",
            agent_role="worker",
            payload={"objective": task.objective},
        )
        dependency_text = "\n".join(
            f"- {task_id}: {text[:1500]}" for task_id, text in dependencies.items()
        )
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Original task:\n{instruction}\n\n"
                    f"Your subtask ({task.id}):\n{task.objective}\n\n"
                    f"Write scope (advisory): {list(task.write_scope)}\n"
                    f"Dependency results:\n{dependency_text or '(none)'}\n\n"
                    "Complete your subtask, verify it, and report a concise result."
                ),
            },
        ]
        iterations = 0
        final_text = ""
        while iterations < args.max_tool_iterations:
            iterations += 1
            response = await call_model(
                messages,
                agent_id=worker_id,
                node_id=f"worker-{task.id}",
                tools=TOOL_SCHEMAS,
                max_tokens=args.max_tokens,
            )
            message = response.choices[0].message
            calls = []
            for call in message.tool_calls or []:
                try:
                    arguments = json.loads(call.function.arguments or "{}")
                except json.JSONDecodeError:
                    arguments = {"_invalid_json": call.function.arguments}
                calls.append({"id": call.id, "name": call.function.name, "arguments": arguments})
            assistant_message: dict[str, Any] = {"role": "assistant", "content": message.content or ""}
            if calls:
                assistant_message["tool_calls"] = [
                    {
                        "id": call["id"],
                        "type": "function",
                        "function": {
                            "name": call["name"],
                            "arguments": json.dumps(call["arguments"], ensure_ascii=False),
                        },
                    }
                    for call in calls
                ]
            messages.append(assistant_message)
            if not calls:
                final_text = message.content or ""
                break
            results = await asyncio.gather(*(invoke_call(call) for call in calls))
            messages.extend(results)
        writer.emit(
            "agent.run.completed",
            agent_id=worker_id,
            parent_agent_id="langgraph-root",
            workflow_id="langgraph-harbor-loop",
            node_id=f"worker-{task.id}",
            agent_role="worker",
            payload={"iterations": iterations, "result_chars": len(final_text)},
        )
        writer.emit(
            "agent.finished",
            agent_id=worker_id,
            parent_agent_id="langgraph-root",
            workflow_id="langgraph-harbor-loop",
            node_id=f"worker-{task.id}",
            agent_role="worker",
            status="completed",
            payload={"iterations": iterations},
        )
        return {
            "id": task.id,
            "objective": task.objective,
            "result": final_text,
            "iterations": iterations,
        }

    async def invoke_call(call: dict[str, Any]) -> dict[str, Any]:
        name = str(call["name"])
        function = tools_by_name.get(name)
        if function is None:
            result = f"Unknown tool: {name}"
        elif "_invalid_json" in call["arguments"]:
            result = f"Invalid JSON arguments: {call['arguments']['_invalid_json']}"
        else:
            try:
                result = await function(**call["arguments"])
            except Exception as exc:
                result = f"{type(exc).__name__}: {exc}"
        return {"role": "tool", "tool_call_id": call["id"], "content": result}

    async def planner_node(state: AgentState) -> AgentState:
        enabled = os.environ.get("HARNESS_LANGGRAPH_PARALLEL_PLAN", "0") == "1"
        if not enabled:
            return {"plan": None}
        try:
            max_tasks = int(os.environ.get("HARNESS_LANGGRAPH_MAX_TASKS", str(MAX_TASKS)))
        except ValueError:
            max_tasks = MAX_TASKS
        response = await call_model(
            planner_messages(instruction, max_tasks),
            agent_id="langgraph-planner",
            node_id="planner",
            tools=None,
            max_tokens=min(2048, args.max_tokens),
        )
        text = response.choices[0].message.content or ""
        plan = validate_plan(parse_plan(text, instruction, max_tasks))
        writer.emit(
            "plan.created",
            agent_id="langgraph-planner",
            workflow_id="langgraph-harbor-loop",
            node_id="planner",
            agent_role="planner",
            planning_level="P1",
            plan_source="model-explicit",
            payload={
                **plan.as_dict(),
                "graph": plan.as_graph(),
                "source": "model-explicit",
                "revision": 1,
            },
        )
        return {"plan": plan.as_dict(), "subtask_results": []}

    async def parallel_workers_node(state: AgentState) -> AgentState:
        raw_plan = state.get("plan") or {}
        tasks = tuple(
            PlanTask(
                id=str(item["id"]),
                objective=str(item["objective"]),
                depends_on=tuple(item.get("depends_on") or ()),
                write_scope=tuple(item.get("write_scope") or ()),
                parallel_group=item.get("parallel_group"),
            )
            for item in raw_plan.get("tasks") or []
        )
        plan = Plan(summary=str(raw_plan.get("summary") or ""), tasks=tasks)
        completed: dict[str, str] = {}
        results: list[dict[str, Any]] = []
        for wave in topological_waves(plan):
            wave_results = await asyncio.gather(
                *(run_worker(task, {dep: completed[dep] for dep in task.depends_on if dep in completed}) for task in wave)
            )
            for result in wave_results:
                completed[result["id"]] = result["result"]
                results.append(result)
                writer.emit(
                    "plan.step.completed",
                    agent_id=f"langgraph-worker-{result['id']}",
                    workflow_id="langgraph-harbor-loop",
                    node_id=f"worker-{result['id']}",
                    payload={"task_id": result["id"], "iterations": result["iterations"]},
                )
        return {"subtask_results": results}

    async def synthesizer_node(state: AgentState) -> AgentState:
        results = state.get("subtask_results") or []
        summary_text = "\n\n".join(
            f"## {item['id']}: {item['objective']}\n{item['result']}" for item in results
        )
        response = await call_model(
            [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"Original task:\n{instruction}\n\n"
                        f"Parallel subtask results:\n{summary_text}\n\n"
                        "Synthesize a concise final answer. Do not repeat the work."
                    ),
                },
            ],
            agent_id="langgraph-synthesizer",
            node_id="synthesizer",
            tools=None,
            max_tokens=min(2048, args.max_tokens),
        )
        final = response.choices[0].message.content or ""
        return {
            "final_answer": final,
            "messages": state["messages"] + [{"role": "assistant", "content": final}],
        }

    async def agent_node(state: AgentState) -> AgentState:
        iterations = int(state.get("iterations", 0)) + 1
        if iterations > args.max_tool_iterations:
            return {
                "messages": state["messages"] + [{
                    "role": "assistant",
                    "content": "Stopped after reaching the tool-iteration safety limit.",
                }],
                "pending_calls": [],
                "iterations": iterations,
            }
        request_id = f"langgraph-model-{iterations}-{uuid.uuid4().hex[:8]}"
        writer.emit(
            "model.request",
            agent_id="langgraph-root",
            workflow_id="langgraph-harbor-loop",
            node_id="agent",
            model=args.model,
            status="started",
            model_request_id=request_id,
            payload={"message_count": len(state["messages"]), "tool_count": len(TOOL_SCHEMAS)},
        )
        try:
            response = await client.chat.completions.create(
                model=args.model,
                messages=state["messages"],
                tools=TOOL_SCHEMAS,
                tool_choice="auto",
                temperature=0,
                max_tokens=args.max_tokens,
                extra_body=model_extra,
            )
        except Exception as exc:
            writer.emit(
                "model.response",
                agent_id="langgraph-root",
                workflow_id="langgraph-harbor-loop",
                node_id="agent",
                model=args.model,
                status="failed",
                error=str(exc),
                model_request_id=request_id,
                payload={"error_type": type(exc).__name__},
            )
            raise
        message = response.choices[0].message
        calls: list[dict[str, Any]] = []
        for call in message.tool_calls or []:
            try:
                arguments = json.loads(call.function.arguments or "{}")
            except json.JSONDecodeError:
                arguments = {"_invalid_json": call.function.arguments}
            calls.append({"id": call.id, "name": call.function.name, "arguments": arguments})
        assistant_message: dict[str, Any] = {
            "role": "assistant",
            "content": message.content or "",
        }
        if calls:
            assistant_message["tool_calls"] = [
                {
                    "id": call["id"],
                    "type": "function",
                    "function": {
                        "name": call["name"],
                        "arguments": json.dumps(call["arguments"], ensure_ascii=False),
                    },
                }
                for call in calls
            ]
        writer.emit(
            "model.response",
            agent_id="langgraph-root",
            workflow_id="langgraph-harbor-loop",
            node_id="agent",
            model=args.model,
            status="completed",
            model_request_id=request_id,
            token_usage=usage_payload(response.usage),
            payload={"finish_reason": response.choices[0].finish_reason, "tool_call_count": len(calls)},
        )
        return {
            "messages": state["messages"] + [assistant_message],
            "pending_calls": calls,
            "iterations": iterations,
        }

    async def tools_node(state: AgentState) -> AgentState:
        calls = list(state.get("pending_calls") or [])

        async def invoke(call: dict[str, Any]) -> dict[str, Any]:
            name = str(call["name"])
            function = tools_by_name.get(name)
            if function is None:
                result = f"Unknown tool: {name}"
            elif "_invalid_json" in call["arguments"]:
                result = f"Invalid JSON arguments: {call['arguments']['_invalid_json']}"
            else:
                try:
                    result = await function(**call["arguments"])
                except Exception as exc:
                    result = f"{type(exc).__name__}: {exc}"
            return {
                "role": "tool",
                "tool_call_id": call["id"],
                "content": result,
            }

        results = await asyncio.gather(*(invoke(call) for call in calls))
        return {
            "messages": state["messages"] + results,
            "pending_calls": [],
            "iterations": state.get("iterations", 0),
        }

    def route(state: AgentState) -> str:
        return "tools" if state.get("pending_calls") else END

    def planner_route(state: AgentState) -> str:
        return "parallel_workers" if state.get("plan") else "agent"

    builder = StateGraph(AgentState)
    builder.add_node("planner", planner_node)
    builder.add_node("agent", agent_node)
    builder.add_node("tools", tools_node)
    builder.add_node("parallel_workers", parallel_workers_node)
    builder.add_node("synthesizer", synthesizer_node)
    builder.add_edge(START, "planner")
    builder.add_conditional_edges(
        "planner",
        planner_route,
        {"agent": "agent", "parallel_workers": "parallel_workers"},
    )
    builder.add_conditional_edges("agent", route, {"tools": "tools", END: END})
    builder.add_edge("tools", "agent")
    builder.add_edge("parallel_workers", "synthesizer")
    builder.add_edge("synthesizer", END)
    graph = builder.compile()
    adapter = LangGraphTelemetryAdapter(
        writer,
        workflow_id="langgraph-harbor-loop",
        workflow_dir=telemetry_dir / "workflow",
        agent_node_ids=(),
        harness="langgraph",
        root_agent_id="langgraph-root",
        cyclic_node_ids={"agent", "tools"},
    )
    initial: AgentState = {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": instruction},
        ],
        "pending_calls": [],
        "iterations": 0,
        "plan": None,
        "subtask_results": [],
    }
    workflow_summary = await adapter.run(
        graph,
        initial,
        config={
            "configurable": {"thread_id": os.environ.get("HARNESS_TRIAL_ID", "trial")},
            # One tool round traverses both the agent and tools nodes.  Keep
            # LangGraph's graph-step guard above our explicit model/tool guard
            # so the runner can end cleanly instead of raising at step 25.
            "recursion_limit": args.max_tool_iterations * 2 + 5,
        },
    )
    write_harbor_summary(
        telemetry_dir, events_path, workflow_summary, harness="langgraph"
    )
    print(json.dumps({
        "status": "completed",
        "iterations": max(adapter.node_attempts.get("agent", 0), 1),
        "workflow_summary": str(telemetry_dir / "workflow" / "workflow-summary.json"),
    }, ensure_ascii=False))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--instruction-file", type=Path, required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--workspace", default="/app")
    parser.add_argument("--max-tool-iterations", type=int, default=50)
    parser.add_argument("--max-tokens", type=int, default=8192)
    return asyncio.run(run(parser.parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
