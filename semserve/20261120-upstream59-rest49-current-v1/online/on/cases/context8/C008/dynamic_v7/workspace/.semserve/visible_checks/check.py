import unittest
import json
import hashlib

API_BOUNDARY_REQUIREMENTS = [
    {
        "target_path": "solution.py",
        "function": "transform",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": False,
                "contract_path": "TASK.md",
                "requirement_quote": "输入seed为整数，records每项含table/id/tenant/subject/time",
                "reason": "TASK.md does not state that non-finite values must raise ValueError; only the normal input domain is specified.",
            },
            "invalid_payload_type": {
                "applicable": False,
                "contract_path": "TASK.md",
                "requirement_quote": "输入seed为整数，records每项含table/id/tenant/subject/time",
                "reason": "TASK.md does not require ValueError on invalid payload types; only the normal input domain is specified.",
            },
        },
    },
]


def _token(seed, tenant, subject):
    raw = json.dumps([str(seed), tenant, subject], ensure_ascii=True, separators=(",", ":")).encode("utf-8")
    return "ref_" + hashlib.sha256(raw).hexdigest()[:12]


class TestTransform(unittest.TestCase):
    def test_output_shape_and_order(self):
        payload = {
            "seed": 7,
            "records": [
                {"table": "t1", "id": "a", "tenant": "x", "subject": "s", "time": 0},
                {"table": "t2", "id": "b", "tenant": "y", "subject": "s", "time": 0},
            ],
            "links": [],
            "merges": [],
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertIsInstance(result, dict)
        self.assertEqual(set(result.keys()), {"records"})
        recs = result["records"]
        self.assertEqual(len(recs), 2)
        self.assertEqual([r["table"] for r in recs], ["t1", "t2"])
        self.assertEqual([r["id"] for r in recs], ["a", "b"])
        for r in recs:
            self.assertEqual(set(r.keys()), {"table", "id", "time", "token"})
            self.assertNotIn("tenant", r)
            self.assertNotIn("subject", r)

    def test_token_derivation(self):
        payload = {
            "seed": 3,
            "records": [{"table": "t", "id": "i", "tenant": "a", "subject": "b", "time": 0}],
            "links": [],
            "merges": [],
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        expected = _token(3, "a", "b")
        self.assertEqual(result["records"][0]["token"], expected)

    def test_seed_changes_token(self):
        base = {"records": [{"table": "t", "id": "i", "tenant": "a", "subject": "b", "time": 0}], "links": [], "merges": []}
        r1 = call_candidate("solution.py", "transform", args=[{**base, "seed": 1}])
        r2 = call_candidate("solution.py", "transform", args=[{**base, "seed": 2}])
        self.assertNotEqual(r1["records"][0]["token"], r2["records"][0]["token"])

    def test_merge_interval_boundaries(self):
        payload = {
            "seed": 1,
            "records": [
                {"table": "t", "id": "i", "tenant": "a", "subject": "s", "time": 10},
                {"table": "t", "id": "j", "tenant": "a", "subject": "t", "time": 10},
            ],
            "links": [],
            "merges": [{"a": ["a", "s"], "b": ["a", "t"], "from": 5, "to": 10}],
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        recs = result["records"]
        self.assertNotEqual(recs[0]["token"], recs[1]["token"])

    def test_merge_active_merges(self):
        payload = {
            "seed": 1,
            "records": [
                {"table": "t", "id": "i", "tenant": "a", "subject": "s", "time": 9},
                {"table": "t", "id": "j", "tenant": "a", "subject": "t", "time": 9},
            ],
            "links": [],
            "merges": [{"a": ["a", "s"], "b": ["a", "t"], "from": 5, "to": 10}],
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        recs = result["records"]
        self.assertEqual(recs[0]["token"], recs[1]["token"])

    def test_canonical_lexicographic_min(self):
        payload = {
            "seed": 1,
            "records": [
                {"table": "t", "id": "i", "tenant": "b", "subject": "z", "time": 0},
                {"table": "t", "id": "j", "tenant": "a", "subject": "y", "time": 0},
            ],
            "links": [{"a": ["b", "z"], "b": ["a", "y"]}],
            "merges": [],
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        recs = result["records"]
        expected = _token(1, "a", "y")
        self.assertEqual(recs[0]["token"], expected)
        self.assertEqual(recs[1]["token"], expected)

    def test_transitive_closure(self):
        payload = {
            "seed": 1,
            "records": [
                {"table": "t", "id": "i", "tenant": "a", "subject": "x", "time": 0},
                {"table": "t", "id": "j", "tenant": "a", "subject": "z", "time": 0},
            ],
            "links": [
                {"a": ["a", "x"], "b": ["a", "y"]},
                {"a": ["a", "y"], "b": ["a", "z"]},
            ],
            "merges": [],
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        recs = result["records"]
        self.assertEqual(recs[0]["token"], recs[1]["token"])

    def test_input_not_mutated(self):
        payload = {
            "seed": 1,
            "records": [{"table": "t", "id": "i", "tenant": "a", "subject": "b", "time": 0}],
            "links": [],
            "merges": [],
        }
        snapshot = json.dumps(payload, sort_keys=True)
        call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(json.dumps(payload, sort_keys=True), snapshot)


if __name__ == "__main__":
    unittest.main()
