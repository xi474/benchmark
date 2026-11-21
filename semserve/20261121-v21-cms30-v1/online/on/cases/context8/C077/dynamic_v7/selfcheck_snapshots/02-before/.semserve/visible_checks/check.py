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
                "requirement_quote": "核心接口transform(payload)返回下述JSON结果，不修改输入对象",
                "reason": "Contract does not specify ValueError for non-object payload types.",
            },
        },
    },
]


class TestTransformBehavior(unittest.TestCase):
    def test_public_fixture_shape(self):
        payload = {"events": [
            {"time": 0, "op": "refresh"},
            {"time": 1, "op": "response", "id": "fetch-1", "items": ["a"]},
        ]}
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertIsInstance(result, dict)
        for key in ("fetches", "commits", "events", "state"):
            self.assertIn(key, result)
        self.assertEqual(result["fetches"], [{"id": "fetch-1", "time": 0}])
        self.assertEqual(result["commits"], [{"time": 1, "items": ["a"]}])
        self.assertEqual(result["state"]["items"], ["a"])
        self.assertFalse(result["state"]["loading"])
        self.assertFalse(result["state"]["owed"])
        self.assertIsNone(result["state"]["in_flight"])
        self.assertIsNone(result["state"]["retry_at"])

    def test_input_not_mutated(self):
        payload = {"events": [
            {"time": 0, "op": "refresh"},
            {"time": 1, "op": "response", "id": "fetch-1", "items": ["a"]},
        ]}
        snapshot = {"events": [dict(e) for e in payload["events"]]}
        call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(payload, snapshot)

    def test_failed_response_schedules_retry(self):
        payload = {"events": [
            {"time": 0, "op": "refresh"},
            {"time": 1, "op": "response", "id": "fetch-1", "failed": True},
        ]}
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(result["state"]["retry_at"], 2001)
        self.assertEqual(result["state"]["in_flight"], "fetch-1")
        self.assertTrue(result["state"]["loading"])
        self.assertEqual(result["state"]["items"], [])
        self.assertEqual(result["commits"], [])
        retries = [e for e in result["events"] if e["event"] == "retry_scheduled"]
        self.assertEqual(len(retries), 1)
        self.assertEqual(retries[0]["reason"], "failure")
        self.assertEqual(retries[0]["due"], 2001)

    def test_stale_response_schedules_retry(self):
        payload = {"events": [
            {"time": 0, "op": "refresh"},
            {"time": 1, "op": "response", "id": "fetch-1", "stale": 1},
        ]}
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(result["state"]["retry_at"], 1001)
        self.assertEqual(result["state"]["in_flight"], "fetch-1")
        retries = [e for e in result["events"] if e["event"] == "retry_scheduled"]
        self.assertEqual(len(retries), 1)
        self.assertEqual(retries[0]["reason"], "stale")
        self.assertEqual(retries[0]["due"], 1001)

    def test_modification_blocks_fetch(self):
        payload = {"events": [
            {"time": 0, "op": "refresh"},
            {"time": 1, "op": "start", "id": "m1"},
            {"time": 2, "op": "finish", "id": "m1"},
        ]}
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(result["fetches"][0], {"id": "fetch-1", "time": 0})
        self.assertEqual(result["fetches"][-1], {"id": "fetch-2", "time": 2})
        self.assertEqual(result["state"]["active"], [])

    def test_retry_after_timer_with_modification(self):
        payload = {"events": [
            {"time": 0, "op": "refresh"},
            {"time": 1, "op": "response", "id": "fetch-1", "failed": True},
            {"time": 2001, "op": "start", "id": "m1"},
            {"time": 2002, "op": "finish", "id": "m1"},
        ]}
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(result["fetches"][-1], {"id": "fetch-3", "time": 2002})
        self.assertIsNone(result["state"]["retry_at"])
        self.assertEqual(result["state"]["in_flight"], "fetch-3")


if __name__ == "__main__":
    unittest.main()
