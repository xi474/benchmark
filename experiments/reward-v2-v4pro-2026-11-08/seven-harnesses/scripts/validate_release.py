"""Verify the sanitized release without access to raw trials or credentials."""
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import re

root = Path(__file__).resolve().parents[1]
audit = json.loads((root / "audit.json").read_text(encoding="utf-8"))
for name, expected in audit["artifact_sha256"].items():
    if sha256((root / name).read_bytes()).hexdigest() != expected:
        raise ValueError("Artifact checksum mismatch: " + name)
data = json.loads((root / "results.json").read_text(encoding="utf-8"))
rows, repeats = data["baseline_cells"], data["latte_independent_repeats"]
assert len(rows) == 392 and len(repeats) == 4
assert len({(r["arm"], r["task"]) for r in rows}) == 392
counts = Counter((r["arm"], r["dataset"]) for r in rows)
for arm in {r["arm"] for r in rows}:
    for dataset, n in (("original14",14),("mixed16-v4",16),("medium26",26)):
        assert counts[(arm,dataset)] == n
for row in rows + repeats:
    assert len(row["score_sha256"]) == len(row["result_sha256"]) == 64
    assert row["e2e_seconds"] is None or row["e2e_seconds"] >= 0
    if row["tokens_status"] == "observed":
        assert row["model_requests_unknown"] == 0
        assert row["tokens_total"] == row["tokens_input"] + row["tokens_output"]
    if row["tokens_status"] == "partial_unknown_request":
        assert row["tokens_total"] is None and row["model_requests_unknown"] > 0
    if row["api_accuracy"] is not None:
        assert row["integrity_ok"] is True and row["score_status"] == "scored"
        assert abs(row["api_accuracy"] - row["api_passed"] / row["api_total"]) < 1e-12
    if row["classification"] in ("invalid_submission","evidence_failed","skipped_pre_send_budget_cap"):
        assert row["api_accuracy"] is None
for summary in data["summary"]:
    group = [r for r in rows if (r["arm"],r["dataset"]) == (summary["arm"],summary["dataset"])]
    valid = [r for r in group if r["api_accuracy"] is not None]
    assert summary["api_passed"] == sum(r["api_passed"] for r in valid)
    assert summary["api_total"] == sum(r["api_total"] for r in valid)
    if valid:
        assert abs(summary["api_micro_accuracy"] - summary["api_passed"]/summary["api_total"]) < 1e-12
        assert abs(summary["api_macro_accuracy"] - sum(r["api_accuracy"] for r in valid)/len(valid)) < 1e-12
multi = json.loads((root / "runtime-multiagent-audit.json").read_text(encoding="utf-8"))
assert multi["release_results_sha256"] == sha256((root / "results.json").read_bytes()).hexdigest()
assert len(multi["latte"]) == len(multi["langgraph"]) == 56
assert multi["summary"]["latte"]["with_teammate_model_responses"] == sum(r["responding_teammates"] > 0 for r in multi["latte"])
assert multi["summary"]["latte"]["model_dynamic_discovery_runs"] == sum(r["model_discover_task_during_execution"] > 0 for r in multi["latte"])
assert multi["summary"]["langgraph"]["parallel_worker_runs"] == sum(r["worker_width"] > 1 for r in multi["langgraph"])
assert multi["summary"]["codex"]["positive_runs"] == len(multi["summary"]["codex"]["examples"])
for row in multi["latte"] + multi["langgraph"]:
    assert len(row["events_sha256"]) == 64
for path in root.rglob("*"):
    if path.is_file():
        text = path.read_text(encoding="utf-8-sig")
        forbidden = [r"(?i)(?<![A-Za-z0-9_-])sk-[A-Za-z0-9_-]{16,}", r"gh[pousr]_[A-Za-z0-9]{20,}",
                     r"(?i)Bearer\s+[A-Za-z0-9._-]{12,}", r"(?i)mlp.ppt24",
                     r"(?i)[A-Z]:[\\/]+Users[\\/]", r"/mnt/c/Users/"]
        for pattern in forbidden:
            # The validation program itself documents the rejected patterns.
            if path != Path(__file__) and re.search(pattern,text):
                raise ValueError("Sensitive material check failed in " + path.name)
print(json.dumps({"status":"passed","baseline_cells":392,"independent_repeats":4,
                  "summaries":len(data["summary"]),"artifact_checksums":"passed",
                  "data_consistency":"passed","sensitive_material_scan":"passed"}))
