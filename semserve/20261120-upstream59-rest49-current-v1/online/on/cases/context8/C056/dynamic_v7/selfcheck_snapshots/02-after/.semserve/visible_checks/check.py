import unittest

# Injected names provided by the SDK runner.
try:
    from visible_contract_check_sdk import call_candidate, CandidateCallError, check_api_boundary
except Exception:
    call_candidate = None
    CandidateCallError = None
    check_api_boundary = None


API_BOUNDARY_REQUIREMENTS = [
    {
        "target_path": "solution.py",
        "function": "transform",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": False,
                "contract_path": "TASK.md",
                "requirement_quote": "输入 tasks 是无序、无环的任务图，各项含 id、needs、pool、stream、attempts。",
                "reason": "The public spec does not state that unknown fields or non-finite values must raise ValueError.",
            },
            "invalid_payload_type": {
                "applicable": False,
                "contract_path": "TASK.md",
                "requirement_quote": "实现 solution.py 中的 transform(payload)，返回题面指定的 JSON 值并保持输入值完整。",
                "reason": "The public spec does not declare ValueError for invalid payload types.",
            },
        },
    },
]


class TestTransform(unittest.TestCase):
    def test_public_fixture(self):
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
        expected = {
            "tasks": {
                "a": {"host": "h", "items": [2, 3], "base": 2, "parent": 0, "delta": 9, "attempts": 1},
                "b": {"host": "k", "items": [1, 2], "base": -1, "parent": 0, "delta": 1, "attempts": 2},
                "c": {"host": "h", "items": [-1], "base": 11, "parent": 10, "delta": 110, "attempts": 3},
            },
            "facts": {"h": 121, "k": 0},
            "pool_reads": {"p": 2, "q": 1},
            "feed_reads": {
                "h": {"s": 2, "t": 0},
                "k": {"s": 0, "t": 1},
            },
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(result, expected)

    def test_single_task_no_deps(self):
        # One task, one host, one batch: base=5, items=[1,2], parent=0.
        payload = {
            "initial": {"h": 5},
            "pools": {"p": ["h"]},
            "feeds": {"h": {"s": [[1, 2]]}},
            "tasks": [{"id": "a", "needs": [], "pool": "p", "stream": "s", "attempts": 1}],
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(result["tasks"]["a"]["delta"], 13)  # (5+1)+(5+2)
        self.assertEqual(result["facts"]["h"], 18)
        self.assertEqual(result["pool_reads"]["p"], 1)
        self.assertEqual(result["feed_reads"]["h"]["s"], 1)

    def test_round_robin_pool_wraps(self):
        # Pool with two hosts, two tasks in same round -> hosts alternate.
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

    def test_parent_delta_sum(self):
        # b depends on a; b's parent is a's committed delta.
        payload = {
            "initial": {"h": 0},
            "pools": {"p": ["h"]},
            "feeds": {"h": {"s": [[1], [2]]}},
            "tasks": [
                {"id": "a", "needs": [], "pool": "p", "stream": "s", "attempts": 1},
                {"id": "b", "needs": ["a"], "pool": "p", "stream": "s", "attempts": 1},
            ],
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        # a: base=0, item=1 -> delta=1. b: base=1 (after a commits), item=2, parent=1 -> (1+2)*(1+1)=6.
        self.assertEqual(result["tasks"]["a"]["delta"], 1)
        self.assertEqual(result["tasks"]["b"]["parent"], 1)
        self.assertEqual(result["tasks"]["b"]["delta"], 6)
        self.assertEqual(result["facts"]["h"], 7)


if __name__ == "__main__":
    unittest.main()
