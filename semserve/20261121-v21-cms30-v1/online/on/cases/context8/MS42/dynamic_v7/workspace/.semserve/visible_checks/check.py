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
                "reason": "No public rule requires rejecting non-finite values in unknown fields.",
            },
            "invalid_payload_type": {
                "applicable": False,
                "contract_path": "TASK.md",
                "requirement_quote": "实现 solution.py 中的 transform(payload)，返回题面指定的 JSON 值并保持输入值完整。",
                "reason": "No public rule specifies ValueError for a non-object payload.",
            },
        },
    },
]


class TestIntegration(unittest.TestCase):
    def test_public_output_shape(self):
        # Output contract: raw container type and required fields.
        res = call_candidate("solution.py", "transform", args=[{
            "rubrics": {"a": ["X", "Y"], "b": ["Y", "X"]},
            "courses": {
                "ENG-2013J": {"items": [["p", "a", [30]], ["q", "b", [80, None]]], "edges": []},
                "ENG-2014J": {"items": [["r", "X", [70]], ["s", "Y", [40]]], "edges": []},
            },
        }])
        self.assertIsInstance(res, dict)
        self.assertEqual(set(res.keys()), {"pairs", "support", "ways", "forced", "drift"})
        self.assertEqual(res["pairs"], 2)
        self.assertEqual(res["support"], 2)
        self.assertEqual(res["ways"], 2)
        self.assertEqual(res["forced"], [])
        self.assertEqual(res["drift"], [[0, 1], [0, 1]])

    def test_empty_alignment_drift_null(self):
        # Valid rare path: no comparable course -> pairs 0 -> drift null.
        res = call_candidate("solution.py", "transform", args=[{
            "rubrics": {"a": ["X"]},
            "courses": {
                "ENG-2013J": {"items": [["p", "a", [30]]], "edges": []},
            },
        }])
        self.assertEqual(res["pairs"], 0)
        self.assertEqual(res["support"], 0)
        self.assertIsNone(res["drift"])
        self.assertEqual(res["forced"], [])


if __name__ == "__main__":
    unittest.main()
