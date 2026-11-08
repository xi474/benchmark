"""Audit runtime multi-agent evidence for selected reward-v2 attempts, offline."""
import argparse
from collections import Counter, defaultdict
from hashlib import sha256
import json
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--outputs-root", type=Path, required=True)
parser.add_argument("--release-root", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
ROOT, RELEASE, OUTPUT = args.outputs_root, args.release_root, args.output
rows = json.loads((RELEASE / "results.json").read_text(encoding="utf-8"))["baseline_cells"]


def read_events(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def parallel_width(spans):
    events = []
    for actor, start, end in spans:
        if start is not None and end is not None and end >= start:
            events.extend(((start, 1, actor), (end, -1, actor)))
    active = Counter()
    maximum = 0
    for _, delta, actor in sorted(events):
        active[actor] += delta
        maximum = max(maximum, sum(n > 0 for n in active.values()))
    return maximum


def latte(row):
    trial = (ROOT / row["result_locator"]).parent
    path = trial / "agent/latte-run/events.jsonl"
    if not path.is_file():
        return {"task": row["task"], "events_missing": True}
    events = read_events(path)
    responders = {e["agent"] for e in events if e.get("type") == "agent_reply"
                  and e.get("agent") not in (None, "Lead", "System")}
    starts, turns, tools = {}, [], []
    for e in events:
        typ, span, actor = e.get("type"), e.get("span_id"), e.get("agent")
        if typ in ("agent_turn_started", "tool.started") and span:
            starts[(typ, span)] = e
        if typ in ("agent_turn_finished", "tool.finished") and span:
            first = starts.get(("agent_turn_started" if typ == "agent_turn_finished" else "tool.started", span))
            if first and actor not in (None, "Lead", "System"):
                record = (actor, first.get("ts"), e.get("ts"))
                (turns if typ == "agent_turn_finished" else tools).append(record)
    discovered = [e for e in events if e.get("type") == "discover_task"
                  and e.get("agent") not in (None, "System")]
    dynamic = [e for e in discovered if (e.get("round") or 0) > 0]
    result = {
        "task": row["task"], "classification": row["classification"],
        "responding_teammates": len(responders),
        "model_discover_task": len(discovered),
        "model_discover_task_during_execution": len(dynamic),
        "system_discover_task": sum(e.get("type") == "discover_task" and e.get("agent") == "System" for e in events),
        "teammate_turn_width": parallel_width(turns),
        "teammate_tool_width": parallel_width(tools),
        "events_source": str(path.relative_to(ROOT)).replace("\\", "/"),
        "events_sha256": sha256(path.read_bytes()).hexdigest(),
    }
    if dynamic:
        result["dynamic_agents"] = dict(Counter(e.get("agent") for e in dynamic))
    return result


def langgraph(row):
    trial = (ROOT / row["result_locator"]).parent
    path = trial / "agent/telemetry/events-v2.jsonl"
    es = read_events(path)
    starts, spans = {}, []
    worker_replies = set()
    for e in es:
        actor = e.get("agent_id") or ""
        if not actor.startswith("langgraph-worker-"):
            continue
        if e.get("event_type") == "model.response":
            worker_replies.add(actor)
        if e.get("event_type") == "agent.run.started":
            identity = (actor, e.get("node_id"))
            if identity in starts:
                raise ValueError("Repeated worker start requires explicit lifecycle matching")
            starts[identity] = e
        if e.get("event_type") == "agent.run.completed" and (actor, e.get("node_id")) in starts:
            start = starts.pop((actor, e.get("node_id")))
            spans.append((actor, start.get("monotonic_ns"), e.get("monotonic_ns")))
    return {"task": row["task"], "workers_with_responses": len(worker_replies),
            "worker_width": parallel_width(spans),
            "events_source": str(path.relative_to(ROOT)).replace("\\", "/"),
            "events_sha256": sha256(path.read_bytes()).hexdigest()}


latte_rows = [latte(r) for r in rows if r["arm"] == "latte-planning-adapted"]
lang_rows = [langgraph(r) for r in rows if r["arm"] == "langgraph"]
summary = {
    "latte": {
        "runs": len(latte_rows),
        "with_teammate_model_responses": sum(r.get("responding_teammates", 0) > 0 for r in latte_rows),
        "with_multiple_teammate_model_responses": sum(r.get("responding_teammates", 0) > 1 for r in latte_rows),
        "teammate_turn_parallel_runs": sum(r.get("teammate_turn_width", 0) > 1 for r in latte_rows),
        "teammate_tool_parallel_runs": sum(r.get("teammate_tool_width", 0) > 1 for r in latte_rows),
        "max_teammate_turn_width": max(r.get("teammate_turn_width", 0) for r in latte_rows),
        "max_teammate_tool_width": max(r.get("teammate_tool_width", 0) for r in latte_rows),
        "model_dynamic_discovery_runs": sum(r.get("model_discover_task_during_execution", 0) > 0 for r in latte_rows),
        "model_dynamic_discoveries": sum(r.get("model_discover_task_during_execution", 0) for r in latte_rows),
        "events_missing_runs": sum(r.get("events_missing", False) for r in latte_rows),
    },
    "langgraph": {
        "runs": len(lang_rows),
        "worker_response_runs": sum(r["workers_with_responses"] > 0 for r in lang_rows),
        "two_worker_response_runs": sum(r["workers_with_responses"] > 1 for r in lang_rows),
        "parallel_worker_runs": sum(r["worker_width"] > 1 for r in lang_rows),
        "max_worker_width": max(r["worker_width"] for r in lang_rows),
        "worker_count_distribution": dict(Counter(r["workers_with_responses"] for r in lang_rows)),
    },
    "latte_dynamic_examples": [r for r in latte_rows if r.get("model_discover_task_during_execution")][:6],
}

roma_rows = [r for r in rows if r["arm"] == "roma"]
summary["roma"] = {
    "runs": len(roma_rows),
    "recursive_child_runs": sum((r.get("roma_actual_child_solve_instances") or 0) > 0 for r in roma_rows),
    "recursive_subplan_runs": sum((r.get("roma_recursive_subplans") or 0) > 0 for r in roma_rows),
    "leaf_parallel_runs": sum((r.get("roma_leaf_executor_parallel_width") or 0) > 1 for r in roma_rows),
    "tool_parallel_runs": sum((r.get("roma_tool_parallel_width") or 0) > 1 for r in roma_rows),
    "max_leaf_parallel_width": max(r.get("roma_leaf_executor_parallel_width") or 0 for r in roma_rows),
    "max_tool_parallel_width": max(r.get("roma_tool_parallel_width") or 0 for r in roma_rows),
    "max_runtime_created_agent_definitions": max(r.get("roma_runtime_created_agent_definitions") or 0 for r in roma_rows),
}
codex_rows = [r for r in rows if r["arm"] == "codex"]
codex_positive = []
for row in codex_rows:
    if not (row.get("observed_subagent_count_reported") or 0) > 0:
        continue
    directory = (ROOT / row["result_locator"]).parent / "agent/monitoring"
    native = directory / "native-codex-observation.json"
    loops_path = directory / "outcome-loops.json"
    native_summary = directory / "native-telemetry/summary.json"
    s = json.loads(native_summary.read_text(encoding="utf-8"))
    loops = json.loads(loops_path.read_text(encoding="utf-8"))
    terminal = s.get("native_descendant_terminal_states") or {}
    delivery = loops.get("delivery_summary") or {}
    codex_positive.append({
        "task": row["task"], "reported_children": s.get("observed_subagent_count"),
        "model_tool_spawn_observed": s.get("model_tool_spawn_observed"),
        "autonomous_delegation": s.get("autonomous_delegation"),
        "completed_children": sum(value == "completed" for value in terminal.values()),
        "parent_received": delivery.get("parent_received"),
        "entered_model_request": delivery.get("entered_model_request"),
        "explicit_sent_events": delivery.get("sent"),
        "explicit_sent_event_coverage": "unavailable",
        "tool_parallel_execution": "unknown",
        "sources": [{"locator": p.relative_to(ROOT).as_posix(),
                     "sha256": sha256(p.read_bytes()).hexdigest()}
                    for p in (native, loops_path, native_summary)],
    })
summary["codex"] = {"runs": len(codex_rows), "positive_runs": len(codex_positive),
                    "examples": codex_positive}
summary["other_harnesses"] = {
    arm: {"runs": sum(r["arm"] == arm for r in rows),
          "reported_subagent_positive_runs": sum(r["arm"] == arm and
              (r.get("observed_subagent_count_reported") or 0) > 0 for r in rows),
          "interpretation": "not observed in this selected reward-v2 cohort"}
    for arm in ("nanobot", "opencode", "dsh")
}
pilot = ROOT / "aorchestra-offline-20261107/mp17-finalization-r2/paid-pilot/pilot-analysis.json"
if pilot.is_file():
    p = json.loads(pilot.read_text(encoding="utf-8"))
    summary["non_matrix_aorchestra_mp17_pilot"] = {
        "scope": "independent MP17 pilot; excluded from seven-arm counts",
        "model": "deepseek-v4-pro", "mode": "non-thinking",
        "delegation_created": p["lifecycle_events"].get("delegation.created"),
        "delegation_completed": p["lifecycle_events"].get("delegation.completed"),
        "subagent_count": p["topology"]["subagent_count"],
        "max_concurrent_subagents": p["topology"]["max_concurrent_subagents"],
        "parallel_agents_observed": p["topology"]["parallel_agents_observed"],
        "source_locator": pilot.relative_to(ROOT).as_posix(),
        "source_sha256": sha256(pilot.read_bytes()).hexdigest(),
    }

print(json.dumps(summary, ensure_ascii=False, indent=2))
OUTPUT.write_text(
    json.dumps({"summary": summary, "latte": latte_rows, "langgraph": lang_rows,
                "release_results_sha256": sha256((RELEASE / "results.json").read_bytes()).hexdigest(),
                "methods": {
                    "latte_turns": "Explicit span_id pairs; different non-Lead/non-System teammates; ts wall clock seconds within native process.",
                    "latte_tools": "Explicit run_script/run_tests span_id pairs; synchronous subprocess boundaries.",
                    "dynamic_tasks": "Accepted discover_task with round>0, excluding System auto-injected fixes.",
                    "langgraph_workers": "Unique agent_id and node_id lifecycle pairs; monotonic_ns intervals."
                }},
               ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
