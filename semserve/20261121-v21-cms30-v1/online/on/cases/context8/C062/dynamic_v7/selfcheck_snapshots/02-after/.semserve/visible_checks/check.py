import unittest


class TestTransformContract(unittest.TestCase):
    def test_open_close_basic(self):
        payload = {
            "events": [
                {"time": 0, "store": "s", "op": "open", "backend": "git"},
                {"time": 1, "store": "s", "op": "close"},
            ]
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(
            result,
            {
                "events": [
                    {"time": 0, "store": "s", "event": "opened"},
                    {"time": 1, "store": "s", "event": "close_returned"},
                ],
                "stores": {
                    "s": {
                        "backend": "git",
                        "state": "closed",
                        "job": None,
                        "revision": 0,
                        "closed_at": 1,
                        "updates": 0,
                    }
                },
            },
        )

    def test_poll_complete_changed(self):
        payload = {
            "events": [
                {"time": 0, "store": "s", "op": "open", "backend": "git"},
                {"time": 1, "store": "s", "op": "poll", "job": "j1"},
                {"time": 2, "store": "s", "op": "complete", "job": "j1", "changed": True, "revision": 5},
                {"time": 3, "store": "s", "op": "close"},
            ]
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(
            [e["event"] for e in result["events"]],
            ["opened", "poll_started", "snapshot_updated", "close_returned"],
        )
        self.assertEqual(result["stores"]["s"]["revision"], 5)
        self.assertEqual(result["stores"]["s"]["updates"], 1)

    def test_poll_coalesced_and_unchanged(self):
        payload = {
            "events": [
                {"time": 0, "store": "s", "op": "open", "backend": "git"},
                {"time": 1, "store": "s", "op": "poll", "job": "j1"},
                {"time": 2, "store": "s", "op": "poll", "job": "j2"},
                {"time": 3, "store": "s", "op": "complete", "job": "j1", "changed": False},
                {"time": 4, "store": "s", "op": "close"},
            ]
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(
            [e["event"] for e in result["events"]],
            ["opened", "poll_started", "poll_coalesced", "poll_unchanged", "close_returned"],
        )
        self.assertEqual(result["stores"]["s"]["revision"], 0)
        self.assertEqual(result["stores"]["s"]["updates"], 0)

    def test_close_barrier_cancel(self):
        payload = {
            "events": [
                {"time": 0, "store": "s", "op": "open", "backend": "git"},
                {"time": 1, "store": "s", "op": "poll", "job": "j1"},
                {"time": 2, "store": "s", "op": "close"},
                {"time": 3, "store": "s", "op": "complete", "job": "j1", "changed": True, "revision": 9},
            ]
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(
            [e["event"] for e in result["events"]],
            ["opened", "poll_started", "cancel_sent", "close_waiting", "callback_cancelled", "close_returned"],
        )
        self.assertEqual(result["stores"]["s"]["revision"], 0)
        self.assertEqual(result["stores"]["s"]["updates"], 0)
        self.assertEqual(result["stores"]["s"]["state"], "closed")

    def test_poll_rejected_when_closing(self):
        payload = {
            "events": [
                {"time": 0, "store": "s", "op": "open", "backend": "git"},
                {"time": 1, "store": "s", "op": "poll", "job": "j1"},
                {"time": 2, "store": "s", "op": "close"},
                {"time": 3, "store": "s", "op": "poll", "job": "j2"},
                {"time": 4, "store": "s", "op": "complete", "job": "j1", "changed": False},
            ]
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertIn("poll_rejected", [e["event"] for e in result["events"]])

    def test_input_not_mutated(self):
        payload = {
            "events": [
                {"time": 0, "store": "s", "op": "open", "backend": "git"},
                {"time": 1, "store": "s", "op": "close"},
            ]
        }
        snapshot = __import__("json").dumps(payload)
        call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(__import__("json").dumps(payload), snapshot)


if __name__ == "__main__":
    unittest.main()
