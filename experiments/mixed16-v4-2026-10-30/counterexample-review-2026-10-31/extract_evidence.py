"""Read-only extraction of local source and native trace evidence.

No model calls, candidate execution, or hidden-test reads are performed.
Outputs are written beside this script, never into the experiment directories.
"""

from __future__ import annotations

import argparse
import os
import ast
import hashlib
import json
import re
from pathlib import Path


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def events(path: Path):
    for line_no, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            yield line_no, obj


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", type=Path, default=Path(
        Path(__file__).resolve().parent / "snapshots"
    ))
    args = parser.parse_args()
    base = args.base.resolve()
    if os.name == "nt" and not str(base).startswith("\\\\?\\"):
        base = Path("\\\\?\\" + str(base))
    out = Path(__file__).resolve().parent / "_recheck"
    if os.name == "nt" and not str(out).startswith("\\\\?\\"):
        out = Path("\\\\?\\" + str(out))
    out.mkdir(exist_ok=True)
    research = base / "harness-v3-research"
    experiment = base / "xi474-benchmark/experiments/mixed16-v4-2026-10-30"

    specs = {
        "S01": ("harness-v3-research/harbor-agents/harbor_agents/cli_agents.py", [(25, 55), (81, 119), (122, 186)]),
        "S02": ("harness-v3-research/harbor-agents/config/codex-model-catalog.json", []),
        "S03": ("harness-v3-research/vendor/codex/codex-rs/models-manager/prompt.md", [(125, 125), (149, 155)]),
        "S04": ("harness-v3-research/vendor/codex/codex-rs/core/src/session/turn.rs", [(162, 173), (580, 610), (723, 759), (1672, 1694)]),
        "S05": ("harness-v3-research/vendor/opencode/packages/opencode/src/session/system.ts", [(31, 52)]),
        "S06": ("harness-v3-research/vendor/opencode/packages/opencode/src/session/llm/request.ts", [(56, 78)]),
        "S07": ("harness-v3-research/vendor/opencode/packages/opencode/src/session/prompt/default.txt", [(70, 78)]),
        "S08": ("harness-v3-research/vendor/opencode/packages/opencode/src/session/prompt.ts", [(1103, 1116), (1178, 1179), (1264, 1285), (1319, 1335)]),
        "S09": ("harness-v3-research/harbor-agents/harbor_agents/framework_runner_common.py", [(116, 120)]),
        "S10": ("harness-v3-research/harbor-agents/harbor_agents/langgraph_runner.py", [(223, 227), (475, 496), (542, 545)]),
        "S11": ("xi474-benchmark/mixed16-precise-spec-v4/tasks/reasoning4/batch_scheduler_transition_spec_v4/workspace/README.md", [(24, 26), (55, 57)]),
        "S12": ("xi474-benchmark/harbor-tasks-mixed16-v4/mixed16-v4-batch_scheduler_transition_spec_v4/task.toml", [(1, 28)]),
        "S13": ("harness-v3-monitoring-workspace/mixed16-v4-workflow-dag.mmd", [(1, 45)]),
        "S14": ("harness-v3-research/harbor-agents/docker/xi474-harness-base.Dockerfile", [(1, 20)]),
        "S15": ("xi474-benchmark/mixed16-precise-spec-v4/tasks/reasoning4/batch_scheduler_transition_spec_v4/TASK.md", [(1, 7)]),
        "S16": ("xi474-benchmark/mixed16-precise-spec-v4/tasks/reasoning4/batch_scheduler_transition_spec_v4/workspace/check.py", [(1, 26)]),
    }
    source_records = []
    excerpts = ["# 源码摘录（原文件只读）", "", "行号按本次本地文件的物理行计；catalog 的 prompt 单独解码。", ""]
    for sid, (rel, ranges) in specs.items():
        path = base / rel
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines()
        record = {"id": sid, "path": str(path), "sha256": digest(path), "line_count": len(lines), "ranges": ranges}
        source_records.append(record)
        excerpts.extend([f"## {sid}", "", f"源文件：`{path}`", "", f"SHA-256：`{record['sha256']}`", ""])
        if sid == "S02":
            catalog = json.loads(text)
            prompt = next(m for m in catalog["models"] if m["slug"] == "deepseek-v4-pro")["base_instructions"]
            source_prompt = (research / "vendor/codex/codex-rs/models-manager/prompt.md").read_text(encoding="utf-8")
            record["decoded_prompt_equal_to_S03"] = prompt == source_prompt
            record["decoded_prompt_sha256_utf8"] = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
            record["decoded_prompt_chars"] = len(prompt)
            model = next(m for m in catalog["models"] if m["slug"] == "deepseek-v4-pro")
            record["selected_model_metadata"] = {k: model[k] for k in ["slug", "context_window", "apply_patch_tool_type", "shell_type", "supported_reasoning_levels"] if k in model}
            excerpts.extend([f"解码后与 S03 文本完全相等：`{prompt == source_prompt}`；字符数：`{len(prompt)}`。", ""])
        for first, last in ranges:
            excerpts.extend(["```text", *[f"{n}: {lines[n-1]}" for n in range(first, min(last, len(lines)) + 1)], "```", ""])

    repos = json.loads((Path(__file__).resolve().parent / "version-provenance.json").read_text(encoding="utf-8"))["repository_metadata"]

    selected = {
        ("codex", "batch_scheduler_transition_spec_v4"): {34, 36, 37, 41, 47, 49, 51, 57, 59, 61, 63, 65, 67, 73, 75, 77},
        ("opencode", "batch_scheduler_transition_spec_v4"): {96, 97, 100, 101, 104, 105, 113, 114, 121, 127, 130, 138, 148, 149, 152, 153},
        ("opencode", "tenant_quota_rebalance_spec_v4"): {42, 45, 76, 79, 80, 83, 84, 87, 88, 91, 104, 200},
    }
    trace_records = []
    inventory = []
    for harness, filename in [("codex", "codex.txt"), ("opencode", "opencode.txt")]:
        for path in sorted((experiment / "traces" / harness).glob(f"*/{filename}")):
            task = path.parent.name
            counts = {}
            picked = []
            for line, event in events(path):
                typ = event.get("type", "")
                counts[typ] = counts.get(typ, 0) + 1
                item = event.get("item", {})
                state = event.get("part", {}).get("state", {})
                output = item.get("aggregated_output", "") if harness == "codex" else state.get("output", "")
                command = item.get("command", "") if harness == "codex" else state.get("input", {}).get("command", "")
                public_pass = bool(
                    re.search(r"python(?:3)?\s+(?:[^\s]*?/)?check\.py", command)
                    and re.search(r"(?m)^LOCAL_CHECKS_PASSED;", str(output))
                )
                if (harness, task) in selected and (line in selected[harness, task] or public_pass or typ in ["turn.completed", "turn.failed"]):
                    picked.append({"line": line, "event": event})
            inventory.append({"harness": harness, "task": task, "path": str(path), "sha256": digest(path), "event_counts": counts})
            if picked:
                result_path = experiment / "results" / harness / task / "summary.json"
                trace_records.append({"harness": harness, "task": task, "path": str(path), "sha256": digest(path), "selected_events": picked, "result_path": str(result_path), "result_sha256": digest(result_path), "result": json.loads(result_path.read_text(encoding="utf-8"))})

    payload = {
        "analysis_date_local": "2026-10-31",
        "timezone": "Asia/Shanghai",
        "scope": "Offline structural scan of 32 native traces; detailed illustrative audit of 3 traces. Not a prevalence or causal-effect estimate.",
        "original_files_modified": False,
        "hidden_test_files_read": False,
        "source_records": source_records,
        "repository_metadata": repos,
        "trace_inventory": inventory,
        "detailed_cases": trace_records,
        "limitations": [
            "Current file hashes establish the audit snapshot, not historical trial provenance.",
            "Native Codex file_change events name changed paths but do not contain full historical diffs.",
            "Reasoning and textual completion messages establish reported intent only.",
            "No paid API calls, benchmark reruns, counterfactual tests, or hidden-oracle reads were performed.",
        ],
    }
    # Independently check the small public-spec witness logged by OpenCode.
    # This does not execute the historical implementation or a hidden oracle.
    case = next(c for c in trace_records if c["harness"] == "opencode" and c["task"] == "batch_scheduler_transition_spec_v4")
    mismatch = next(r for r in case["selected_events"] if r["line"] == 105)
    logged_output = mismatch["event"]["part"]["state"]["output"]
    start = logged_output.index("[")
    end = logged_output.index("]", start) + 1
    windows = ast.literal_eval(logged_output[start:end])
    cooldown = int(logged_output[end:].splitlines()[0].strip())
    feasible = []
    for mask in range(1 << len(windows)):
        subset = [w for i, w in enumerate(windows) if mask & (1 << i)]
        ordered = sorted(subset, key=lambda w: (w["start"], w["end"], w["id"]))
        if all(a["end"] + cooldown <= z["start"] for a, z in zip(ordered, ordered[1:])):
            feasible.append({"value": sum(w["value"] for w in subset), "selected": sorted(w["id"] for w in subset)})
    best = min(feasible, key=lambda v: (-v["value"], v["selected"]))
    witness = {"source_trace": case["path"], "source_trace_sha256": case["sha256"], "source_line": 105, "windows": windows, "cooldown": cooldown, "subsets_enumerated": 1 << len(windows), "independent_expected": best, "historical_candidate_output": {"selected": ["w24"], "value": 9}, "historical_candidate_executed_in_this_audit": False, "public_spec_source_id": "S11"}
    payload["independently_checked_witness"] = witness
    (out / "oracle-witness.json").write_text(json.dumps(witness, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out / "evidence.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out / "source-excerpts.md").write_text("\n".join(excerpts), encoding="utf-8")
    print(json.dumps({"sources": len(source_records), "native_traces_scanned": len(inventory), "detailed_cases": len(trace_records), "prompt_text_equal": next(s for s in source_records if s["id"] == "S02")["decoded_prompt_equal_to_S03"], "outputs": [str(out / "evidence.json"), str(out / "source-excerpts.md")]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
