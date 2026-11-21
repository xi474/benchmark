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
                "reason": "The public spec does not require rejecting non-finite values in unknown fields.",
            },
            "invalid_payload_type": {
                "applicable": False,
                "contract_path": "TASK.md",
                "requirement_quote": "实现 solution.py 中的 transform(payload)，返回题面指定的 JSON 值并保持输入值完整。",
                "reason": "The public spec does not state that transform must raise ValueError on invalid payload types.",
            },
        },
    },
]


class TestTransform(unittest.TestCase):
    def test_public_fixture(self):
        payload = {
            "rubrics": {"a": ["X", "Y"], "b": ["Y", "X"]},
            "courses": {
                "ENG-2013J": {"items": [["p", "a", [30]], ["q", "b", [80, None]]], "edges": []},
                "ENG-2014J": {"items": [["r", "X", [70]], ["s", "Y", [40]]], "edges": []},
            },
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(result["pairs"], 2)
        self.assertEqual(result["support"], 2)
        self.assertEqual(result["ways"], 2)
        self.assertEqual(result["forced"], [])
        self.assertEqual(result["drift"], [[0, 1], [0, 1]])

    def test_order_constraint_forces_single_alignment(self):
        payload = {
            "rubrics": {"a": ["X", "Y"], "b": ["Y", "X"]},
            "courses": {
                "M-2013J": {"items": [["p", "a", [10, 20]], ["q", "b", [30]]], "edges": [["p", "q"]]},
                "M-2014J": {"items": [["r", "X", [15]], ["s", "Y", [25, 35]]], "edges": [["r", "s"]]},
            },
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(result["pairs"], 2)
        self.assertEqual(result["support"], 2)
        self.assertEqual(result["ways"], 1)
        self.assertEqual(result["forced"], [["M", "p", "r"], ["M", "q", "s"]])
        self.assertEqual(result["drift"], [[5, 1], [5, 1]])

    def test_empty_alignment_drift_null(self):
        payload = {
            "rubrics": {"a": ["X"]},
            "courses": {
                "C-2013J": {"items": [["p", "a", [None]]], "edges": []},
                "C-2014J": {"items": [["r", "X", [None]]], "edges": []},
            },
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(result["pairs"], 0)
        self.assertEqual(result["support"], 0)
        self.assertEqual(result["ways"], 1)
        self.assertEqual(result["forced"], [])
        self.assertIsNone(result["drift"])


if __name__ == "__main__":
    unittest.main()
