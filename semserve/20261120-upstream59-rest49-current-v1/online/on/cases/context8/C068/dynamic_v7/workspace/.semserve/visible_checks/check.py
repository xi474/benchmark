import unittest

API_BOUNDARY_REQUIREMENTS = [
    {
        "target_path": "solution.py",
        "function": "transform",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": False,
                "contract_path": "TASK.md",
                "requirement_quote": "不要求额外NaN/Infinity防御",
                "reason": "Public contract explicitly excludes NaN/Infinity defense.",
            },
            "invalid_payload_type": {
                "applicable": False,
                "contract_path": "TASK.md",
                "requirement_quote": "输入ttl为正整数",
                "reason": "Public contract does not require ValueError on invalid payload types.",
            },
        },
    }
]


class TestTransform(unittest.TestCase):
    def test_shared_inflight_join(self):
        payload = {
            "ttl": 5,
            "events": [
                {"op": "get", "time": 0, "id": "a", "key": "k", "delay": 3, "value": 1, "error": None},
                {"op": "get", "time": 1, "id": "b", "key": "k", "delay": 9, "value": 9, "error": None},
                {"op": "advance", "time": 3},
            ],
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(len(result["loads"]), 1)
        self.assertEqual(result["loads"][0]["key"], "k")
        self.assertEqual(result["loads"][0]["started_at"], 0)
        self.assertEqual(result["loads"][0]["finished_at"], 3)
        self.assertEqual(result["results"][0]["value"], 1)
        self.assertEqual(result["results"][1]["value"], 1)
        self.assertEqual(result["results"][1]["finished_at"], 3)

    def test_cancel_waiter_keeps_load(self):
        payload = {
            "ttl": 5,
            "events": [
                {"op": "get", "time": 0, "id": "a", "key": "k", "delay": 3, "value": 1, "error": None},
                {"op": "get", "time": 1, "id": "b", "key": "k", "delay": 3, "value": 2, "error": None},
                {"op": "cancel", "time": 2, "id": "b"},
                {"op": "advance", "time": 3},
            ],
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(len(result["loads"]), 1)
        # results are ordered by get order: a first, b second
        self.assertEqual(result["results"][0]["id"], "a")
        self.assertEqual(result["results"][0]["status"], "ok")
        self.assertEqual(result["results"][1]["id"], "b")
        self.assertEqual(result["results"][1]["status"], "cancelled")
        self.assertEqual(result["results"][1]["error"], "cancelled")
        self.assertEqual(result["cache"][0]["value"], 1)

    def test_error_cached_value_null(self):
        payload = {
            "ttl": 5,
            "events": [
                {"op": "get", "time": 0, "id": "a", "key": "k", "delay": 0, "value": 7, "error": "boom"},
            ],
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(result["results"][0]["status"], "error")
        self.assertEqual(result["results"][0]["value"], None)
        self.assertEqual(result["results"][0]["error"], "boom")
        self.assertEqual(result["cache"][0]["error"], "boom")
        self.assertEqual(result["cache"][0]["value"], 7)

    def test_expiry_eviction(self):
        payload = {
            "ttl": 5,
            "events": [
                {"op": "get", "time": 0, "id": "a", "key": "k", "delay": 0, "value": 1, "error": None},
                {"op": "get", "time": 6, "id": "b", "key": "k", "delay": 0, "value": 2, "error": None},
            ],
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(len(result["loads"]), 2)
        self.assertEqual(result["results"][1]["value"], 2)

    def test_next_cleanup_initial(self):
        payload = {"ttl": 5, "events": []}
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(result["next_cleanup"], 80)


if __name__ == "__main__":
    unittest.main()
