import unittest


API_BOUNDARY_REQUIREMENTS = [
    {
        "target_path": "solution.py",
        "function": "transform",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": False,
                "contract_path": "TASK.md",
                "requirement_quote": "实现 solution.py 中的 transform(payload)，返回题面指定的 JSON 值并保持输入值完整。",
                "reason": "The public spec does not state that transform must reject non-finite values or unknown fields; it only requires returning the specified JSON value.",
            },
            "invalid_payload_type": {
                "applicable": False,
                "contract_path": "TASK.md",
                "requirement_quote": "实现 solution.py 中的 transform(payload)，返回题面指定的 JSON 值并保持输入值完整。",
                "reason": "The public spec does not document a ValueError contract for non-object payloads.",
            },
        },
    },
]


class TestTransformBehavior(unittest.TestCase):
    def test_public_fixture_output(self):
        # Independent re-derivation of the public example via the full pipeline.
        payload = {
            "initial": {"h": 2, "k": -1},
            "pools": {"p": ["k", "h"], "q": ["h"]},
            "feeds": {
                "h": {"s": [[2, 3], [-1]], "t": [[1], []]},
                "k": {"s": [[4], [3]], "t": [[1, 2], [0]]},
            },
            "tasks": [
                {"id": "c", "needs": ["a", "b"], "pool": "p", "stream": "s", "attempts": 3},
                {"id": "b", "needs": [], "pool": "p", "stream": "t", "attempts": 2},
                {"id": "a", "needs": [], "pool": "q", "stream": "s", "attempts": 1},
            ],
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertIsInstance(result, dict)
        self.assertEqual(set(result), {"tasks", "facts", "pool_reads", "feed_reads"})
        self.assertEqual(result["tasks"]["a"]["host"], "h")
        self.assertEqual(result["tasks"]["a"]["items"], [2, 3])
        self.assertEqual(result["tasks"]["a"]["base"], 2)
        self.assertEqual(result["tasks"]["a"]["parent"], 0)
        self.assertEqual(result["tasks"]["a"]["delta"], 9)
        self.assertEqual(result["tasks"]["b"]["host"], "k")
        self.assertEqual(result["tasks"]["b"]["delta"], 1)
        self.assertEqual(result["tasks"]["c"]["host"], "h")
        self.assertEqual(result["tasks"]["c"]["base"], 11)
        self.assertEqual(result["tasks"]["c"]["parent"], 10)
        self.assertEqual(result["tasks"]["c"]["delta"], 110)
        self.assertEqual(result["facts"], {"h": 121, "k": 0})
        self.assertEqual(result["pool_reads"], {"p": 2, "q": 1})
        self.assertEqual(result["feed_reads"], {"h": {"s": 2, "t": 0}, "k": {"s": 0, "t": 1}})

    def test_input_not_mutated(self):
        payload = {
            "initial": {"h": 0},
            "pools": {"p": ["h"]},
            "feeds": {"h": {"s": [[1]]}},
            "tasks": [{"id": "a", "needs": [], "pool": "p", "stream": "s", "attempts": 1}],
        }
        snapshot = {
            "initial": dict(payload["initial"]),
            "pools": {k: list(v) for k, v in payload["pools"].items()},
            "feeds": {h: {s: [list(b) for b in bs] for s, bs in st.items()} for h, st in payload["feeds"].items()},
            "tasks": [dict(t) for t in payload["tasks"]],
        }
        call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(payload, snapshot)

    def test_single_task_delta(self):
        # base=5, item=2, parent=0 -> (5+2)*1 = 7
        payload = {
            "initial": {"h": 5},
            "pools": {"p": ["h"]},
            "feeds": {"h": {"s": [[2]]}},
            "tasks": [{"id": "a", "needs": [], "pool": "p", "stream": "s", "attempts": 1}],
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(result["tasks"]["a"]["delta"], 7)
        self.assertEqual(result["facts"]["h"], 12)

    def test_parent_delta_used(self):
        # a: base=0, item=1 -> delta 1. b needs a: base=1 (after a commits), item=1,
        # parent=1 -> (1+1)*(1+1)=4.
        payload = {
            "initial": {"h": 0},
            "pools": {"p": ["h"]},
            "feeds": {"h": {"s": [[1], [1]]}},
            "tasks": [
                {"id": "a", "needs": [], "pool": "p", "stream": "s", "attempts": 1},
                {"id": "b", "needs": ["a"], "pool": "p", "stream": "s", "attempts": 1},
            ],
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(result["tasks"]["a"]["delta"], 1)
        self.assertEqual(result["tasks"]["b"]["base"], 1)
        self.assertEqual(result["tasks"]["b"]["parent"], 1)
        self.assertEqual(result["tasks"]["b"]["delta"], 4)
        self.assertEqual(result["facts"]["h"], 5)

    def test_pool_round_robin_and_feed_cycle(self):
        # Two tasks in the same wave, ascending id order, pool cycles h->k.
        # a (id "a") gets h, b (id "b") gets k.
        payload = {
            "initial": {"h": 0, "k": 0},
            "pools": {"p": ["h", "k"]},
            "feeds": {"h": {"s": [[1]]}, "k": {"s": [[2]]}},
            "tasks": [
                {"id": "a", "needs": [], "pool": "p", "stream": "s", "attempts": 1},
                {"id": "b", "needs": [], "pool": "p", "stream": "s", "attempts": 1},
            ],
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(result["tasks"]["a"]["host"], "h")
        self.assertEqual(result["tasks"]["b"]["host"], "k")
        self.assertEqual(result["pool_reads"]["p"], 2)
        self.assertEqual(result["feed_reads"]["h"]["s"], 1)
        self.assertEqual(result["feed_reads"]["k"]["s"], 1)


if __name__ == "__main__":
    unittest.main()
