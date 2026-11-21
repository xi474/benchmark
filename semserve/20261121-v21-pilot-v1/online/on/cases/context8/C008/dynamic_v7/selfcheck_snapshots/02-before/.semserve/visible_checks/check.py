import json
import unittest

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# Visible documents used for requirement citations.
TASK = str(ROOT / "TASK.md")
CONTRACT = str(ROOT / "contract.json")

API_BOUNDARY_REQUIREMENTS = [
    {
        "target_path": "solution.py",
        "function": "transform",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": False,
                "contract_path": TASK,
                "requirement_quote": "只验公开输入域与核心业务约束，不验任意异常文本或编码风格。",
                "reason": "The visible spec explicitly declines to validate arbitrary malformed text; non-finite values are outside the declared normal input domain.",
            },
            "invalid_payload_type": {
                "applicable": False,
                "contract_path": TASK,
                "requirement_quote": "只验公开输入域与核心业务约束，不验任意异常文本或编码风格。",
                "reason": "The visible spec does not require ValueError for a non-object payload; only the normal input domain is validated.",
            },
        },
    },
]


class TestTokenContract(unittest.TestCase):
    def test_token_format_and_seed_sensitivity(self):
        # token = "ref_" + first 12 lowercase hex of SHA256 of
        # json.dumps([str(seed), tenant, subject], ensure_ascii=True, separators=(",",":"))
        payload = {
            "seed": 7,
            "records": [
                {"table": "t", "id": "r1", "tenant": "a", "subject": "x", "time": 0},
            ],
            "links": [],
            "merges": [],
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        token = result["records"][0]["token"]
        self.assertTrue(token.startswith("ref_"), token)
        self.assertEqual(len(token), 16, token)
        self.assertTrue(all(c in "0123456789abcdef" for c in token[4:]), token)

        # Changing the seed must change the token.
        payload2 = json.loads(json.dumps(payload))
        payload2["seed"] = 8
        result2 = call_candidate("solution.py", "transform", args=[payload2])
        self.assertNotEqual(token, result2["records"][0]["token"])

    def test_canonical_lexicographic_min_and_cross_table_shared_token(self):
        # Two records in the same component at the same time must share a token,
        # and the canonical subject is the lexicographically smallest (tenant, subject).
        payload = {
            "seed": 1,
            "records": [
                {"table": "orders", "id": "o1", "tenant": "a", "subject": "t", "time": 1},
                {"table": "history", "id": "v1", "tenant": "a", "subject": "s", "time": 7},
                {"table": "events", "id": "e1", "tenant": "b", "subject": "u", "time": 7},
            ],
            "links": [
                {"a": ["b", "u"], "b": ["a", "t"]},
            ],
            "merges": [
                {"a": ["a", "s"], "b": ["a", "t"], "from": 5, "to": 10},
            ],
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        recs = result["records"]
        self.assertEqual(len(recs), 3)
        # At time 7, (a,s) and (b,u) are connected via (a,t): same token.
        self.assertEqual(recs[1]["token"], recs[2]["token"])
        # At time 1, no active relationship: distinct token.
        self.assertNotEqual(recs[0]["token"], recs[1]["token"])

    def test_output_shape_preserves_order_and_public_fields(self):
        payload = {
            "seed": 1,
            "records": [
                {"table": "orders", "id": "o1", "tenant": "a", "subject": "t", "time": 1},
                {"table": "history", "id": "v1", "tenant": "a", "subject": "s", "time": 7},
                {"table": "events", "id": "e1", "tenant": "b", "subject": "u", "time": 7},
            ],
            "links": [],
            "merges": [],
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertIsInstance(result, dict)
        self.assertEqual(set(result.keys()), {"records"})
        recs = result["records"]
        self.assertEqual([r["table"] for r in recs], ["orders", "history", "events"])
        self.assertEqual([r["id"] for r in recs], ["o1", "v1", "e1"])
        self.assertEqual([r["time"] for r in recs], [1, 7, 7])
        for r in recs:
            self.assertEqual(set(r.keys()), {"table", "id", "time", "token"})
            self.assertNotIn("tenant", r)
            self.assertNotIn("subject", r)


if __name__ == "__main__":
    unittest.main()
