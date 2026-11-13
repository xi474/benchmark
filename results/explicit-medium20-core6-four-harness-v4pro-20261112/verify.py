"""Offline verification of the published, redacted results package. No API calls."""
from pathlib import Path
import csv
import hashlib
import json
import math
from collections import Counter, defaultdict
from datetime import datetime

ROOT = Path(__file__).resolve().parent


def read_csv(name):
    with (ROOT / name).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def number(row, key):
    assert row[key] != "", (row.get("trial_id"), key, "missing")
    return float(row[key])


def same(a, b):
    assert math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-6), (a, b)


def main():
    expected = {}
    for line in (ROOT / "SHA256SUMS").read_text(encoding="utf8").splitlines():
        digest, name = line.split("  ", 1)
        assert name not in expected and Path(name).name == name
        expected[name] = digest
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name
    assert set(expected) == {p.name for p in ROOT.iterdir() if p.is_file()} - {"SHA256SUMS"}
    cells = read_csv("completed_cells.csv")
    by_id = {r["trial_id"]: r for r in cells}
    assert len(cells) == len(by_id) == 205
    assert Counter(r["arm"] for r in cells) == {"explicit": 101, "native": 104}
    assert all(r["scored"] == "True" and r["core_metrics_ready"] == "True" for r in cells)
    assert sum(r["harness"] == "codex" for r in cells) == 49
    assert all("unverified" in r["mode_status"] for r in cells if r["harness"] == "codex")
    requests = read_csv("request_usage.csv")
    assert len({r["request_ref"] for r in requests}) == len(requests) == 10552
    request_groups = defaultdict(list)
    for r in requests:
        assert r["trial_id"] in by_id
        request_groups[r["trial_id"]].append(r)
        assert 0 <= number(r, "input_cached_tokens") <= number(r, "input_tokens")
        price = ((number(r, "input_tokens") - number(r, "input_cached_tokens")) * 1.32
                 + number(r, "input_cached_tokens") * .044 + number(r, "output_tokens") * 3.96) / 1e6
        same(price, number(r, "estimated_usd"))
    checks = read_csv("verifier_checks.csv")
    check_groups = defaultdict(list)
    assert len({(r["trial_id"], r["check_id"]) for r in checks}) == len(checks)
    for r in checks:
        assert r["trial_id"] in by_id and r["passed"] in {"True", "False"}
        assert (r["is_api"] == "True") == r["check_id"].startswith("api/")
        check_groups[r["trial_id"]].append(r)
    coverage = {r["trial_id"]: r for r in read_csv("coverage.csv")}
    assert set(coverage) == set(by_id)
    for identity, r in by_id.items():
        same((datetime.fromisoformat(r["harbor_finished_at"]) - datetime.fromisoformat(r["harbor_started_at"])).total_seconds(), number(r, "harbor_e2e_sec"))
        assert number(r, "harbor_e2e_sec") >= number(r, "agent_execution_sec") >= 0
        assert number(r, "verifier_sec") >= 0 and number(r, "resource_samples") >= 2
        assert number(r, "unknown_usage_requests") == 0
        api = [c for c in check_groups[identity] if c["is_api"] == "True"]
        same(len(api), number(r, "api_total"))
        same(sum(c["passed"] == "True" for c in api), number(r, "api_pass"))
        same(number(r, "api_pass") / number(r, "api_total"), number(r, "api_accuracy"))
        req = request_groups[identity]
        same(len(req), number(r, "settled_requests"))
        for source, target in [("input_tokens", "input_tokens"), ("output_tokens", "output_tokens"), ("input_cached_tokens", "input_cached_tokens"), ("estimated_usd", "estimated_usd_known_settled"), ("http_duration_sec", "model_http_duration_sum_sec")]:
            same(sum(number(e, source) for e in req), number(r, target))
        same(number(r, "input_tokens") + number(r, "output_tokens"), number(r, "total_tokens"))
        same(number(r, "input_cached_tokens") / number(r, "input_tokens"), number(r, "input_cache_hit_ratio"))
        same(sum(e["reasoning_tokens"] != "" for e in req), number(r, "requests_with_reasoning_field"))
        observed_reasoning = [float(e["reasoning_tokens"]) for e in req if e["reasoning_tokens"] != ""]
        assert bool(observed_reasoning) == bool(r["reasoning_tokens"])
        if observed_reasoning:
            same(sum(observed_reasoning), number(r, "reasoning_tokens"))
        assert coverage[identity]["core_metrics_complete"] == "True"
    agents = read_csv("agents.csv")
    assert len(agents) == len({(r["trial_id"], r["child_id"]) for r in agents}) == 237
    child_counts = Counter(r["trial_id"] for r in agents)
    for identity, r in by_id.items():
        same(child_counts[identity], number(r, "child_count"))
    pairs = read_csv("paired_cells.csv")
    assert len(pairs) == 104 and sum(p["matched_scored"] == "True" for p in pairs) == 101
    for p in pairs:
        if p["matched_scored"] != "True":
            continue
        a, b = p["explicit_trial"], p["native_trial"]
        aset = {c["check_id"] for c in check_groups[a] if c["is_api"] == "True"}
        bset = {c["check_id"] for c in check_groups[b] if c["is_api"] == "True"}
        assert aset == bset
        for prefix, identity in [("explicit", a), ("native", b)]:
            for key in ["api_pass", "api_total"]:
                same(number(p, prefix + "_" + key), number(by_id[identity], key))
    status = read_csv("matrix_status.csv")
    assert len(status) == len({r["trial_id"] for r in status}) == 208
    pending = [r for r in status if r["scored"] == "False"]
    assert {(r["harness"], r["task_id"]) for r in pending} == {("codex", "MP15"), ("codex", "MP17"), ("codex", "MP19")}
    assert all(r["publication_state"] == "pending-rerun-no-score-published" for r in pending)
    for r in read_csv("summary.csv"):
        g = [c for c in cells if all(c[k] == r[k] for k in ["arm", "harness", "dataset"])]
        same(len(g), number(r, "scored"))
        for key in ["api_pass", "api_total", "input_tokens", "output_tokens"]:
            same(sum(number(c, key) for c in g), number(r, key))
        same(sum(number(c, "api_pass") for c in g) / sum(number(c, "api_total") for c in g), number(r, "api_micro"))
        same(sum(number(c, "harbor_e2e_sec") for c in g) / len(g), number(r, "e2e_mean_sec"))
    validation = json.loads((ROOT / "validation.json").read_text(encoding="utf8"))
    assert validation["passed"] is True and validation["all_runtime_metrics_uniformly_complete"] is False
    print(json.dumps({"passed": True, "completed_cells": len(cells), "settled_requests": len(requests), "verifier_checks": len(checks), "child_identities": len(agents), "pending_cells": len(pending), "api_id_matched_pairs": 101, "provider_model_requests": 0}, ensure_ascii=False))


if __name__ == "__main__":
    main()
