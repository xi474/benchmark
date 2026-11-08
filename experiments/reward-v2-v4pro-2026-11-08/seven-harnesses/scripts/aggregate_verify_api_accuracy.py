"""Audit verifier API-check accuracy for certificate-selected reward-v2 cells.

Read-only inputs; no provider calls. A certificate, not a directory sweep, decides
which attempt represents each logical task/Harness cell. Score files supply the
per-check measurements. Missing, duplicate or inconsistent evidence is an error.
"""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from hashlib import sha256
import json
from pathlib import Path
import subprocess


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def score_index(roots: list[Path]) -> dict[str, list[Path]]:
    command = ["rg", "--files", "-g", "score-v2.json", *map(str, roots)]
    found = subprocess.run(command, text=True, capture_output=True, check=True)
    index: dict[str, list[Path]] = defaultdict(list)
    for line in found.stdout.splitlines():
        path = Path(line)
        parts = path.parts
        if path.parent.name != "verifier" or "jobs" not in parts:
            continue
        at = parts.index("jobs")
        if at + 1 >= len(parts):
            continue
        index[parts[at + 1]].append(path)
    return index


def arm_name(value: str) -> str:
    return {
        "latte-native-planning-adapted-v1": "latte-planning-adapted",
        "roma-local-C0-native-recursive": "roma",
    }.get(value, value)


def dataset(task: str) -> str:
    head = task.split("/", 1)[0]
    return {"original": "original14", "hard": "mixed16-v4", "medium": "medium26"}[head]


def ratio(passed: int, total: int) -> float | None:
    return passed / total if total else None


def load_cells(certificate_paths: list[Path]) -> list[dict]:
    rows: list[dict] = []
    keys: set[tuple[str, str]] = set()
    for path in certificate_paths:
        certificate = read(path)
        for cell in certificate["cells"]:
            arm = arm_name(cell.get("harness", certificate.get("harness", "")))
            if not arm:
                raise ValueError(f"missing Harness in {path}")
            task = cell["task"]
            key = (arm, task)
            if key in keys:
                raise ValueError(f"duplicate certified cell {key}")
            keys.add(key)
            rows.append({
                "arm": arm,
                "task": task,
                "dataset": dataset(task),
                "trial_id": cell["trial_id"],
                "classification": cell["classification"],
                "certified_reward": cell["reward"],
                "certified_max_reward": cell["max_reward"],
                "certificate_path": str(path),
                "certificate_sha256": digest(path),
            })
    return rows


def analyze(cells: list[dict], index: dict[str, list[Path]]) -> list[dict]:
    result: list[dict] = []
    for cell in cells:
        paths = index.get(cell["trial_id"], [])
        if not paths and cell["classification"] in {
            "skipped_agent_timeout_unscored", "cancelled", "not_started", "infrastructure_failed"
        }:
            result.append({
                **cell,
                "score_path": None,
                "score_sha256": None,
                "score_status": None,
                "integrity_ok": None,
                "all_checks_passed": None,
                "overall_passed": None,
                "overall_total": None,
                "api_passed": None,
                "api_total": None,
                "api_accuracy": None,
                "focused_passed": None,
                "focused_total": None,
                "focused_accuracy": None,
                "api_accuracy_status": "unscored_" + cell["classification"],
            })
            continue
        if len(paths) != 1:
            raise ValueError(f"expected one score for {cell['trial_id']}, found {len(paths)}")
        path = paths[0]
        score = read(path)
        checks = score.get("checks")
        if score.get("schema") != "benchmark.partial-reward.v2":
            raise ValueError(f"wrong score schema: {path}")
        if score.get("policy_version") != "2.0.0" or score.get("task") != cell["task"]:
            raise ValueError(f"policy/task mismatch: {path}")
        if not isinstance(checks, list) or score.get("total_verifiers") != len(checks):
            raise ValueError(f"check-count mismatch: {path}")
        if score.get("passed_verifiers") != sum(check.get("passed") is True for check in checks):
            raise ValueError(f"passed-count mismatch: {path}")
        if abs(score["reward"] - cell["certified_reward"]) > 0.000001:
            raise ValueError(f"reward differs from certificate: {path}")
        if score["max_reward"] != cell["certified_max_reward"]:
            raise ValueError(f"max reward differs from certificate: {path}")
        ids = [check.get("id") for check in checks]
        if len(ids) != len(set(ids)) or any(not isinstance(x, str) for x in ids):
            raise ValueError(f"invalid or duplicate check IDs: {path}")
        api = [check for check in checks if check["id"].startswith("api/")]
        focused = [check for check in checks if check["id"].startswith("focused/")]
        api_passed = sum(check["passed"] is True for check in api)
        focused_passed = sum(check["passed"] is True for check in focused)
        valid = score.get("integrity_ok") is True and score.get("status") == "scored"
        if cell["classification"] == "invalid_submission" and valid:
            raise ValueError(f"invalid certificate has scored integrity: {path}")
        result.append({
            **cell,
            "score_path": str(path),
            "score_sha256": digest(path),
            "score_status": score["status"],
            "integrity_ok": score["integrity_ok"],
            "all_checks_passed": score["all_checks_passed"],
            "overall_passed": score["passed_verifiers"],
            "overall_total": score["total_verifiers"],
            "api_passed": api_passed,
            "api_total": len(api),
            "api_accuracy": ratio(api_passed, len(api)) if valid else None,
            "focused_passed": focused_passed,
            "focused_total": len(focused),
            "focused_accuracy": ratio(focused_passed, len(focused)) if valid else None,
            "api_accuracy_status": ("invalid_submission" if not valid else
                                    "not_applicable_no_api_checks" if not api else "measured"),
        })
    return result


def summarize(rows: list[dict]) -> list[dict]:
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in rows:
        groups[(row["arm"], row["dataset"])].append(row)
    summary = []
    for (arm, group), items in sorted(groups.items()):
        measured = [row for row in items if row["api_accuracy"] is not None]
        focused = [row for row in items if row["focused_accuracy"] is not None]
        api_pass = sum(row["api_passed"] for row in measured)
        api_total = sum(row["api_total"] for row in measured)
        focused_pass = sum(row["focused_passed"] for row in focused)
        focused_total = sum(row["focused_total"] for row in focused)
        summary.append({
            "arm": arm,
            "dataset": group,
            "certified_cells": len(items),
            "api_measured_cells": len(measured),
            "api_not_applicable_cells": sum(row["api_accuracy_status"] == "not_applicable_no_api_checks" for row in items),
            "invalid_submission_cells": sum(row["api_accuracy_status"] == "invalid_submission" for row in items),
            "unscored_cells": sum(row["api_accuracy_status"].startswith("unscored_") for row in items),
            "api_passed": api_pass,
            "api_total": api_total,
            "api_micro_accuracy": ratio(api_pass, api_total),
            "api_macro_accuracy": sum(row["api_accuracy"] for row in measured) / len(measured) if measured else None,
            "focused_passed": focused_pass,
            "focused_total": focused_total,
            "focused_micro_accuracy": ratio(focused_pass, focused_total),
        })
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--certificate", type=Path, action="append", required=True)
    parser.add_argument("--search-root", type=Path, action="append", required=True)
    parser.add_argument("--output-prefix", type=Path, required=True)
    parser.add_argument("--expect-cells", type=int)
    args = parser.parse_args()
    cells = load_cells(args.certificate)
    if args.expect_cells is not None and len(cells) != args.expect_cells:
        raise ValueError(f"expected {args.expect_cells} certified cells, found {len(cells)}")
    rows = analyze(cells, score_index(args.search_root))
    summary = summarize(rows)
    args.output_prefix.parent.mkdir(parents=True, exist_ok=True)
    csv_path = args.output_prefix.with_suffix(".csv")
    with csv_path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    json_path = args.output_prefix.with_suffix(".json")
    json_path.write_text(json.dumps({"schema": "verifier-api-accuracy.v1", "cells": rows,
                                     "summary": summary}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"cells": len(rows), "api_measured": sum(r["api_accuracy"] is not None for r in rows),
                      "api_not_applicable": sum(r["api_accuracy_status"] == "not_applicable_no_api_checks" for r in rows),
                      "invalid": sum(r["api_accuracy_status"] == "invalid_submission" for r in rows),
                      "unscored": sum(r["api_accuracy_status"].startswith("unscored_") for r in rows),
                      "csv": str(csv_path), "json": str(json_path)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
