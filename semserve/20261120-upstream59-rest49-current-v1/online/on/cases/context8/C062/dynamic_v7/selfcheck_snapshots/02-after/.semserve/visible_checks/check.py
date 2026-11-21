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
                "requirement_quote": "输入events按非递减整数time排列",
                "reason": "Contract does not specify ValueError for invalid payload types.",
            },
        },
    }
]


class TestTransform(unittest.TestCase):
    def test_close_barrier_cancel_then_complete(self):
        payload = {
            "events": [
                {"time": 0, "store": "s", "op": "open", "backend": "git"},
                {"time": 1, "store": "s", "op": "poll", "job": "j1"},
                {"time": 2, "store": "s", "op": "close"},
                {"time": 3, "store": "s", "op": "complete", "job": "j1", "changed": True, "revision": 5},
            ]
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(
            result["events"],
            [
                {"time": 0, "store": "s", "event": "opened"},
                {"time": 1, "store": "s", "event": "poll_started", "job": "j1"},
                {"time": 2, "store": "s", "event": "cancel_sent", "job": "j1"},
                {"time": 2, "store": "s", "event": "close_waiting"},
                {"time": 3, "store": "s", "event": "callback_cancelled", "job": "j1"},
                {"time": 3, "store": "s", "event": "close_returned"},
            ],
        )
        st = result["stores"]["s"]
        self.assertEqual(st["state"], "closed")
        self.assertEqual(st["revision"], 0)
        self.assertEqual(st["updates"], 0)
        self.assertEqual(st["closed_at"], 3)

    def test_poll_coalesced_and_unchanged(self):
        payload = {
            "events": [
                {"time": 0, "store": "s", "op": "open", "backend": "s3"},
                {"time": 1, "store": "s", "op": "poll", "job": "j1"},
                {"time": 2, "store": "s", "op": "poll", "job": "j2"},
                {"time": 3, "store": "s", "op": "complete", "job": "j1", "changed": False},
            ]
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(
            result["events"],
            [
                {"time": 0, "store": "s", "event": "opened"},
                {"time": 1, "store": "s", "event": "poll_started", "job": "j1"},
                {"time": 2, "store": "s", "event": "poll_coalesced"},
                {"time": 3, "store": "s", "event": "poll_unchanged", "job": "j1"},
            ],
        )
        self.assertEqual(result["stores"]["s"]["updates"], 0)

    def test_snapshot_updated_increments(self):
        payload = {
            "events": [
                {"time": 0, "store": "s", "op": "open", "backend": "azure", "revision": 2},
                {"time": 1, "store": "s", "op": "poll", "job": "j1"},
                {"time": 2, "store": "s", "op": "complete", "job": "j1", "changed": True, "revision": 9},
            ]
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(result["stores"]["s"]["revision"], 9)
        self.assertEqual(result["stores"]["s"]["updates"], 1)
        self.assertEqual(result["events"][-1]["event"], "snapshot_updated")

    def test_poll_rejected_when_closed(self):
        payload = {
            "events": [
                {"time": 0, "store": "s", "op": "open", "backend": "oci"},
                {"time": 1, "store": "s", "op": "close"},
                {"time": 2, "store": "s", "op": "poll", "job": "j1"},
            ]
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(result["events"][-1]["event"], "poll_rejected")

    def test_closed_again_close_returns_immediately(self):
        payload = {
            "events": [
                {"time": 0, "store": "s", "op": "open", "backend": "local"},
                {"time": 1, "store": "s", "op": "close"},
                {"time": 2, "store": "s", "op": "close"},
            ]
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(result["events"][-1]["event"], "close_returned")
        self.assertEqual(result["stores"]["s"]["closed_at"], 1)

    def test_input_not_mutated(self):
        payload = {
            "events": [
                {"time": 0, "store": "s", "op": "open", "backend": "git"},
                {"time": 1, "store": "s", "op": "close"},
            ]
        }
        import copy
        before = copy.deepcopy(payload)
        call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(payload, before)


if __name__ == "__main__":
    unittest.main()
