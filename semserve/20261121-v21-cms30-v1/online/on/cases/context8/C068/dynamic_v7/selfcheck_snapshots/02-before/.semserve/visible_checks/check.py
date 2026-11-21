import unittest

API_BOUNDARY_REQUIREMENTS = [
    {
        "target_path": "solution.py",
        "function": "transform",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": False,
                "contract_path": "TASK.md",
                "requirement_quote": "验收覆盖本文正常输入域与完整交付，不要求额外NaN/Infinity防御",
                "reason": "Public contract explicitly excludes NaN/Infinity defense.",
            },
            "invalid_payload_type": {
                "applicable": False,
                "contract_path": "TASK.md",
                "requirement_quote": "输入ttl为正整数；events的time为非负非递减整数",
                "reason": "Contract does not specify ValueError for non-object payloads.",
            },
        },
    },
]


class TestTransformContract(unittest.TestCase):
    def test_public_fixture_matches_expected(self):
        payload = {
            "ttl": 5,
            "events": [
                {"op": "get", "time": 0, "id": "a", "key": "k", "delay": 3, "value": 1, "error": None},
                {"op": "advance", "time": 3},
                {"op": "get", "time": 4, "id": "b", "key": "k", "delay": 3, "value": 9, "error": None},
            ],
        }
        expected = {
            "results": [
                {"id": "a", "status": "ok", "value": 1, "error": None, "finished_at": 3},
                {"id": "b", "status": "ok", "value": 1, "error": None, "finished_at": 4},
            ],
            "loads": [{"key": "k", "started_at": 0, "finished_at": 3}],
            "cache": [{"key": "k", "value": 1, "error": None, "expires": 8}],
            "next_cleanup": 80,
        }
        actual = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(actual, expected)

    def test_cancel_pending_waiter_does_not_cancel_shared_load(self):
        payload = {
            "ttl": 10,
            "events": [
                {"op": "get", "time": 0, "id": "a", "key": "k", "delay": 5, "value": 7, "error": None},
                {"op": "get", "time": 1, "id": "b", "key": "k", "delay": 99, "value": 99, "error": None},
                {"op": "cancel", "time": 2, "id": "b"},
                {"op": "advance", "time": 5},
            ],
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(
            result["results"],
            [
                {"id": "b", "status": "cancelled", "value": None, "error": "cancelled", "finished_at": 2},
                {"id": "a", "status": "ok", "value": 7, "error": None, "finished_at": 5},
            ],
        )
        self.assertEqual(result["loads"], [{"key": "k", "started_at": 0, "finished_at": 5}])
        self.assertEqual(result["cache"], [{"key": "k", "value": 7, "error": None, "expires": 15}])

    def test_error_value_cached_with_null_value(self):
        payload = {
            "ttl": 10,
            "events": [
                {"op": "get", "time": 0, "id": "a", "key": "k", "delay": 2, "value": 5, "error": "boom"},
                {"op": "advance", "time": 2},
                {"op": "get", "time": 3, "id": "b", "key": "k", "delay": 0, "value": 1, "error": None},
            ],
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(result["results"][0]["status"], "error")
        self.assertIsNone(result["results"][0]["value"])
        self.assertEqual(result["results"][0]["error"], "boom")
        self.assertEqual(result["results"][1]["status"], "error")
        self.assertIsNone(result["results"][1]["value"])
        self.assertEqual(result["cache"][0]["error"], "boom")
        self.assertEqual(result["cache"][0]["value"], 5)

    def test_delay_zero_completes_inline(self):
        payload = {
            "ttl": 10,
            "events": [
                {"op": "get", "time": 4, "id": "a", "key": "k", "delay": 0, "value": 3, "error": None},
            ],
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(result["results"][0]["finished_at"], 4)
        self.assertEqual(result["loads"], [{"key": "k", "started_at": 4, "finished_at": 4}])
        self.assertEqual(result["cache"][0]["expires"], 14)

    def test_expired_entry_evicted_on_access(self):
        payload = {
            "ttl": 5,
            "events": [
                {"op": "get", "time": 0, "id": "a", "key": "k", "delay": 3, "value": 1, "error": None},
                {"op": "advance", "time": 3},
                {"op": "get", "time": 9, "id": "b", "key": "k", "delay": 1, "value": 2, "error": None},
                {"op": "advance", "time": 10},
            ],
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(result["loads"], [
            {"key": "k", "started_at": 0, "finished_at": 3},
            {"key": "k", "started_at": 9, "finished_at": 10},
        ])
        self.assertEqual(result["results"][1]["value"], 2)
        self.assertEqual(result["cache"][0]["expires"], 15)

    def test_cleanup_removes_all_expired_at_threshold(self):
        payload = {
            "ttl": 5,
            "events": [
                {"op": "get", "time": 0, "id": "a", "key": "x", "delay": 1, "value": 1, "error": None},
                {"op": "advance", "time": 1},
                {"op": "get", "time": 80, "id": "b", "key": "y", "delay": 0, "value": 2, "error": None},
            ],
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual([c["key"] for c in result["cache"]], ["y"])
        self.assertEqual(result["next_cleanup"], 80 + 16 * 5)


if __name__ == "__main__":
    unittest.main()
