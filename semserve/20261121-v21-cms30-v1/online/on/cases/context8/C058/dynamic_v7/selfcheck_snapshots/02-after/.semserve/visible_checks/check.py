import unittest


class TestTransformContract(unittest.TestCase):
    def test_empty_program_returns_empty_batches_and_ok_final(self):
        payload = {"hosts": ["h0", "h1"], "handlers": [], "program": {}}
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(result["batches"], [])
        self.assertEqual(result["final"], {"h0": "ok", "h1": "ok"})

    def test_input_not_mutated(self):
        payload = {"hosts": ["h0"], "handlers": [], "program": {}}
        snapshot = {"hosts": list(payload["hosts"]), "handlers": list(payload["handlers"]),
                    "program": dict(payload["program"])}
        call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(payload, snapshot)

    def test_single_task_success_produces_task_pair(self):
        payload = {
            "hosts": ["h0"],
            "handlers": [],
            "program": {"tasks": [{"id": "t1"}]},
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(result["final"], {"h0": "ok"})
        self.assertEqual(result["batches"], [
            {"host": "h0", "task": "t1", "kind": "task", "status": "ok"},
        ])

    def test_failing_task_marks_host_failed(self):
        payload = {
            "hosts": ["h0"],
            "handlers": [],
            "program": {"tasks": [{"id": "t1", "fail_hosts": ["h0"]}]},
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(result["final"], {"h0": "failed"})
        self.assertEqual(result["batches"], [
            {"host": "h0", "task": "t1", "kind": "task", "status": "failed"},
        ])

    def test_notify_produces_flush_and_handler(self):
        payload = {
            "hosts": ["h0"],
            "handlers": ["h1"],
            "program": {"tasks": [{"id": "t1", "notify": ["h1"]}]},
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(result["final"], {"h0": "ok"})
        self.assertEqual(result["batches"], [
            {"host": "h0", "task": "t1", "kind": "task", "status": "ok"},
            {"host": "h0", "task": None, "kind": "flush", "status": "ok", "handlers": ["h1"]},
            {"host": "h0", "task": "h1", "kind": "handler", "status": "ok"},
        ])


if __name__ == "__main__":
    unittest.main()
