import json
import unittest

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent

API_BOUNDARY_REQUIREMENTS = [
    {
        "target_path": "solution.py",
        "function": "transform",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": False,
                "contract_path": "TASK.md",
                "requirement_quote": "只验公开输入域与核心业务约束，不验任意异常文本或编码风格。",
                "reason": "Public spec explicitly limits validation to the public input domain and core business constraints; it does not require rejecting non-finite values in unknown fields.",
            },
            "invalid_payload_type": {
                "applicable": False,
                "contract_path": "TASK.md",
                "requirement_quote": "只验公开输入域与核心业务约束，不验任意异常文本或编码风格。",
                "reason": "Public spec does not require ValueError on invalid payload types; only the public input domain is validated.",
            },
        },
    },
]


class TestCanonicalToken(unittest.TestCase):
    def test_public_fixture_tokens(self):
        # Public rule: same canonical subject across tables shares a token.
        payload = json.loads((ROOT / "public_input.json").read_text(encoding="utf-8"))
        result = call_candidate("solution.py", "transform", args=[payload])
        tokens = [r["token"] for r in result["records"]]
        # history (a,s) and events (b,u) merge via link b.u-a.t and merge a.s-a.t at t=7.
        self.assertEqual(tokens[1], tokens[2])
        self.assertNotEqual(tokens[0], tokens[1])

    def test_seed_changes_token(self):
        # Public rule: changing seed must recompute the token.
        payload = json.loads((ROOT / "public_input.json").read_text(encoding="utf-8"))
        r1 = call_candidate("solution.py", "transform", args=[payload])
        payload2 = json.loads(json.dumps(payload))
        payload2["seed"] = 2
        r2 = call_candidate("solution.py", "transform", args=[payload2])
        self.assertNotEqual(r1["records"][0]["token"], r2["records"][0]["token"])

    def test_output_shape_and_order(self):
        # Public rule: preserve record order, row count, and public fields.
        payload = json.loads((ROOT / "public_input.json").read_text(encoding="utf-8"))
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(len(result["records"]), len(payload["records"]))
        for i, rec in enumerate(result["records"]):
            self.assertEqual(set(rec.keys()), {"table", "id", "time", "token"})
            self.assertEqual(rec["table"], payload["records"][i]["table"])
            self.assertEqual(rec["id"], payload["records"][i]["id"])
            self.assertEqual(rec["time"], payload["records"][i]["time"])
            self.assertNotIn("tenant", rec)
            self.assertNotIn("subject", rec)

    def test_token_format(self):
        # Public rule: token is ref_ + 12 lowercase hex chars.
        payload = json.loads((ROOT / "public_input.json").read_text(encoding="utf-8"))
        result = call_candidate("solution.py", "transform", args=[payload])
        for rec in result["records"]:
            self.assertRegex(rec["token"], r"^ref_[0-9a-f]{12}$")

    def test_merge_window_boundaries(self):
        # Public rule: intervals are left-closed right-open; a merge active only
        # within [from, to). At time 10 the merge a.s-a.t is inactive, so a.s and
        # a.t are distinct components.
        payload = {
            "seed": 1,
            "records": [
                {"table": "t1", "id": "1", "tenant": "a", "subject": "s", "time": 10},
                {"table": "t2", "id": "2", "tenant": "a", "subject": "t", "time": 10},
            ],
            "links": [],
            "merges": [
                {"a": ["a", "s"], "b": ["a", "t"], "from": 5, "to": 10},
            ],
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertNotEqual(result["records"][0]["token"], result["records"][1]["token"])

    def test_merge_window_active(self):
        # Same merge active at time 9 merges the two subjects.
        payload = {
            "seed": 1,
            "records": [
                {"table": "t1", "id": "1", "tenant": "a", "subject": "s", "time": 9},
                {"table": "t2", "id": "2", "tenant": "a", "subject": "t", "time": 9},
            ],
            "links": [],
            "merges": [
                {"a": ["a", "s"], "b": ["a", "t"], "from": 5, "to": 10},
            ],
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(result["records"][0]["token"], result["records"][1]["token"])

    def test_tenant_scope_not_mixed(self):
        # Public rule: different tenants with the same subject id must not merge.
        payload = {
            "seed": 1,
            "records": [
                {"table": "t1", "id": "1", "tenant": "a", "subject": "x", "time": 1},
                {"table": "t2", "id": "2", "tenant": "b", "subject": "x", "time": 1},
            ],
            "links": [],
            "merges": [],
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertNotEqual(result["records"][0]["token"], result["records"][1]["token"])

    def test_canonical_lexicographic(self):
        # Public rule: canonical subject is lexicographically smallest (tenant,subject).
        # Merge (b,x) with (a,y): canonical is (a,y).
        payload = {
            "seed": 1,
            "records": [
                {"table": "t1", "id": "1", "tenant": "b", "subject": "x", "time": 1},
                {"table": "t2", "id": "2", "tenant": "a", "subject": "y", "time": 1},
            ],
            "links": [{"a": ["b", "x"], "b": ["a", "y"]}],
            "merges": [],
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(result["records"][0]["token"], result["records"][1]["token"])


if __name__ == "__main__":
    unittest.main()
