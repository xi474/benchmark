"""Rebuild the published SP score table and audit the DSH trace annotation counts."""
import argparse
import csv
import hashlib
import importlib.util
import json
import re
import sys
from collections import Counter
from decimal import Decimal
from pathlib import Path
from zipfile import ZipFile


METRICS = Path("results/upstream59-v21-semserve-vs-six-harnesses-20261123/task-metrics.json")
NATIVE = Path("results/upstream59-v21-native-traces-dsh-codex-nanobot-20261123")
GREEN = re.compile(r"(?im)^\s*(?:public check passed|public pass|公开检查通过|local_checks_passed\b|public_checks_passed\b)")


def check(value, message):
    if not value:
        raise ValueError(message)


def read(path):
    return json.loads(path.read_bytes())


def unique(rows):
    result = {}
    for row in rows:
        key = row["task"]
        check(key not in result, f"Duplicate task {key}")
        result[key] = row
    return result


def find_release(hint):
    for candidate in (hint, *hint.parents):
        if (candidate / METRICS).is_file() and (candidate / "scoring/workspace_reward.py").is_file():
            return candidate
    raise ValueError("Release checkout unavailable. Pass --release-root PATH; see tools/README.md.")


def scoring_module(root):
    spec = importlib.util.spec_from_file_location("review_xi474_reward", root / "scoring/workspace_reward.py")
    module = importlib.util.module_from_spec(spec)
    prior = sys.dont_write_bytecode
    try:
        sys.dont_write_bytecode = True
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = prior
    check(module.SCORING_REVISION == "delivery-bonus-50-v1", "Unexpected scoring policy")
    return module


def receipt(root, task, system, scoring):
    folder = Path(system["trace_evidence"]["trace_path"])
    check(not folder.is_absolute() and ".." not in folder.parts and folder.parts[0] == "semserve", "Unexpected receipt path")
    path = folder / "u59/score.json"
    raw = read(root / path)
    label = f"{task} {path}"
    check(raw["task"] == task and raw["scoring_revision"] == scoring.SCORING_REVISION, label)
    counts = Counter()
    missed = []
    seen = set()
    for row in raw["checks"]:
        cat = row["category"]
        check(cat in ("A", "B", "D", "P") and type(row["passed"]) is bool and row["id"] not in seen, label)
        seen.add(row["id"])
        counts[(cat, row["passed"])] += 1
        if not row["passed"]:
            missed.append({"category": cat, "id": row["id"]})
    passed = sum(n for (_, ok), n in counts.items() if ok)
    api_total = counts["A", True] + counts["A", False]
    check(passed == raw["passed_verifiers"] and len(seen) == raw["total_verifiers"], label)
    check(counts["A", True] == raw["core_transform_cases_passed"] and api_total == raw["core_transform_cases_total"], label)
    check(counts["P", True] + counts["P", False] == 1 and bool(counts["P", True]) == raw["public_pass"], label)
    reward = scoring.task_reward(difficulty=raw["reward_difficulty"], passed=passed, total=len(seen),
                                 strict_pass=raw["strict_pass"], integrity_ok=raw["integrity_ok"])
    check(reward == Decimal(raw["reward"]), label)
    check(set(system["failed_checks"]) == {x["id"] for x in missed}, label)
    fields = ("total_verifiers", "passed_verifiers", "public_pass", "integrity_ok", "strict_pass", "reward",
              "core_transform_cases_passed", "core_transform_cases_total", "max_reward", "reward_difficulty")
    score = {k: raw[k] for k in fields}
    check(all(system["score"][k] == val for k, val in score.items()), label)
    return {**score, "receipt": path.as_posix(), "failed_checks": missed}


def add_scores(rows):
    failed = Counter(q["category"] for a in rows for q in a["failed_checks"])
    return {"tasks": len(rows), "integrity_pass": sum(v["integrity_ok"] for v in rows),
            "strict": sum(v["strict_pass"] for v in rows), "public": sum(v["public_pass"] for v in rows),
            "api_pass": sum(v["core_transform_cases_passed"] for v in rows),
            "api_total": sum(v["core_transform_cases_total"] for v in rows),
            "max_reward": sum(v["max_reward"] for v in rows),
            "reward": str(sum(Decimal(v["reward"]) for v in rows)),
            "failed_by_category": {c:failed[c] for c in "ABDP"}}


def audit_native(root, task, row, official):
    path = root / NATIVE / "dsh" / (task + ".zip")
    check(hashlib.sha256(path.read_bytes()).hexdigest() == row["sha256"], f"{task}: archive hash mismatch")
    with ZipFile(path) as z:
        case = json.loads(z.read("case.json"))
        check(case["selected_attempt"] == official["selected_attempt_id"] == row["attempt"], f"{task}: attempt mismatch")
        events = [json.loads(line) for line in z.read("agent/dsh-stream.jsonl").splitlines() if line.strip()]
    gate = row["gate"]
    if gate is not None:
        check(1 <= gate <= len(events), f"{task}: public-check line out of range")
        evt = events[gate - 1]
        check(evt["type"] == "tool_result" and GREEN.search(str(evt["result"])), f"{task}: public check receipt")
        check(any(v["type"] == "tool_call" and v.get("tool") == "bash" and
                  v.get("callId") == evt["callId"] for v in events[:gate-1]), f"{task}: missing bash call")
        check(all(gate < line <= len(events) for line in row["test_lines"] + row["chain"]), f"{task}: causal order")


def dsh_data(root, evidence, tasks, include_native):
    source = read(evidence / "dsh-postpublic/audit.json")
    cases = unique(source["cases"])
    family_sets = [read(evidence / ("scenario-" + part + ".json")) for part in ("C", "MP", "MSN")]
    scenarios = unique([r for rows in family_sets for r in rows])
    check(set(cases) == set(tasks) == set(scenarios), "DSH task coverage")
    groups = {}
    for name, row in cases.items():
        official = tasks[name]["systems"]["dsh"]
        check(row["strict"] == official["score"]["strict_pass"] and row["attempt"] == official["selected_attempt_id"], name)
        check((row["group"] == "no_gate") == (row["gate"] is None), f"{name}: gate classification")
        texts = scenarios[name]["scenarios"]
        check(all(isinstance(v, str) and v.strip() for v in texts) and len(set(texts)) == len(texts), name)
        check(bool(texts) == (row["group"] == "new"), f"{name}: scenario classification")
        if include_native:
            audit_native(root, name, row, official)
        group = groups.setdefault(row["group"], {"count":0, "strict":0, "confirmed_defect":0, "same_input_pass":0})
        group["count"] += 1
        group["strict"] += row["strict"]
        group["confirmed_defect"] += row["bug"]
        group["same_input_pass"] += row["same_pass"]
    check(groups == source["summary"], "DSH subgroup counts disagree with the frozen audit")
    expected = {"new":(45,33), "interface":(3,1), "replay":(5,2), "no_gate":(6,0)}
    check({k:(v["count"],v["strict"]) for k,v in groups.items()} == expected, "DSH groups")
    return cases, scenarios, {"groups":groups, "public_gate":sum(x["gate"] is not None for x in cases.values()),
        "scenarios_lower_bound": sum(len(x["scenarios"]) for x in scenarios.values()),
        "strict": sum(x["strict"] for x in cases.values()),
        "same_input_repair_tasks": sorted(k for k,x in cases.items() if x["same_pass"]),
        "native_sha256_and_lines_checked": include_native}


def verify(root, evidence, include_native):
    tasks = read(root / METRICS)["tasks"]
    scoring = scoring_module(root)
    grouped = [read(evidence / (part + ".json")) for part in ("C", "MP", "MSN")]
    details = unique([r for rows in grouped for r in rows])
    dsh, scenarios, dsh_summary = dsh_data(root, evidence, tasks, include_native)
    output = []
    for task, data in sorted(tasks.items()):
        first = receipt(root, task, data["systems"]["semserve_first"], scoring)
        attempt = data.get("semserve_replay_attempt")
        check(bool(attempt) == (not first["public_pass"]), f"{task}: replay eligibility")
        replay = receipt(root, task, attempt, scoring) if attempt else None
        use_replay = bool(replay and replay["public_pass"])
        if attempt:
            check(attempt["score_adopted"] == use_replay, f"{task}: replay selection")
        selected = replay if use_replay else first
        identity = "replay" if use_replay else "first"
        pub = data["systems"]["semserve_with_replay"]
        check(pub["score_selected_from"] == identity, task)
        check(all(pub["score"][k] == val for k,val in selected.items() if k not in ("failed_checks","receipt")), task)
        check(set(pub["failed_checks"]) == {x["id"] for x in selected["failed_checks"]}, task)
        output.append({"task":task, "selected_from":identity, "first":first, "replay":replay, "selected":selected,
                       "dsh_group":dsh[task]["group"], "dsh_strict":dsh[task]["strict"],
                       "dsh_scenarios":len(scenarios[task]["scenarios"]) if dsh[task]["gate"] is not None else None,
                       "repair_suggestion":details.get(task, {}).get("improvement")})
    diagnosed = {r["task"] for r in output if not r["first"]["strict_pass"] or not r["selected"]["strict_pass"]}
    check(set(details) == diagnosed, "Diagnosis coverage")
    one = add_scores([v["first"] for v in output])
    final = add_scores([v["selected"] for v in output])
    attempted = [v["task"] for v in output if v["replay"]]
    adopted = [v["task"] for v in output if v["selected_from"] == "replay"]
    recovered = [v["task"] for v in output if not v["first"]["strict_pass"] and v["selected"]["strict_pass"]]
    check((one["tasks"], len(attempted), len(adopted), len(diagnosed), len(recovered)) == (59,9,6,34,3), "SP task audit")
    all_attempts = [v["first"] for v in output] + [v["replay"] for v in output if v["replay"]]
    check(len({a["receipt"] for a in all_attempts}) == len(all_attempts) and all(a["integrity_ok"] for a in all_attempts),
          "Duplicate or integrity-failed receipt")
    check((one["strict"], one["public"], one["api_pass"], one["api_total"], one["reward"]) == (25,50,633,803,"78.469237"), "First aggregate")
    check((final["strict"], final["public"],final["api_pass"],final["api_total"],final["reward"]) == (28,56,669,803,"85.361619"), "Selected aggregate")
    check(final["failed_by_category"] == {"A":134,"B":24,"D":42,"P":3}, "Failed checks")
    check((dsh_summary["public_gate"], dsh_summary["scenarios_lower_bound"], dsh_summary["strict"]) == (53,299,36), "DSH aggregate")
    check(dsh_summary["same_input_repair_tasks"] == ["MP15", "MS02"], "DSH confirmed same-input repairs")
    return {"scoring_revision":scoring.SCORING_REVISION, "receipt_count":len(output)+len(attempted), "first":one,
            "selected":final, "selected_not_strict":len(output)-final["strict"], "diagnosis_count":len(diagnosed),
            "replay_attempted":attempted, "replay_adopted":adopted, "strict_recovered":recovered, "dsh":dsh_summary}, output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release-root", type=Path)
    parser.add_argument("--evidence-dir", type=Path, help="Defaults to the package's evidence/ directory")
    parser.add_argument("--output-dir", type=Path, help="Write review.json and tasks.csv to a new or empty directory")
    parser.add_argument("--skip-native", action="store_true", help="Skip ZIP hash/line validation (requires only score receipts)")
    args = parser.parse_args()
    package = Path(__file__).resolve().parent.parent
    root = find_release((args.release_root or package).resolve())
    summary, rows = verify(root, args.evidence_dir or package / "evidence", not args.skip_native)
    if args.output_dir:
        dest = args.output_dir
        dest.mkdir(parents=True, exist_ok=True)
        check(not any(dest.iterdir()), f"Output directory must be empty: {dest}")
        with (dest / "review.json").open("x", encoding="utf8") as f:
            json.dump({"summary":summary,"tasks":rows},f,ensure_ascii=False,indent=2)
        with (dest / "tasks.csv").open("x", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["task","selected_from","first_api_pass","selected_api_pass","api_total","selected_strict",
                             "reward","failed_API_ids","dsh_group","dsh_new_scenarios","repair_suggestion"])
            for row in rows:
                x=row["selected"]
                writer.writerow([row["task"],row["selected_from"],row["first"]["core_transform_cases_passed"],
                    x["core_transform_cases_passed"],x["core_transform_cases_total"],x["strict_pass"],x["reward"],
                    "|".join(c["id"] for c in x["failed_checks"] if c["category"]=="A"),row["dsh_group"],
                    row["dsh_scenarios"],row["repair_suggestion"]])
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
