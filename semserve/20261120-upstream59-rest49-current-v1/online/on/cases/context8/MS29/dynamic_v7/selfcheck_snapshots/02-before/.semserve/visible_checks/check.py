import unittest

# Visible-contract self-checks for solution.transform.
# The public fixture only exercises two feasible triples; these tests cover
# infeasibility (plan null), distinct-category enforcement, difficulty
# filtering, and the lexicographic tie-break on a hand-derived small case.

API_BOUNDARY_REQUIREMENTS = [
    {
        "target_path": "solution.py",
        "function": "transform",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": False,
                "contract_path": "TASK.md",
                "requirement_quote": "所有数量、价格均为非负整数，并且每个报价的价格为正。",
                "reason": "The public spec does not state that transform must raise ValueError on non-finite or unknown fields; it only constrains numeric ranges.",
            },
            "invalid_payload_type": {
                "applicable": False,
                "contract_path": "TASK.md",
                "requirement_quote": "实现 solution.py 中的 transform(payload)，返回题面指定的 JSON 值并保持输入值完整。",
                "reason": "The spec does not document a ValueError contract for a non-object payload; it only describes the expected JSON output.",
            },
        },
    }
]


def _payload():
    return {
        "dishes": [
            ["a", "cat1", 1, {"x": 1}],
            ["b", "cat2", 1, {"y": 1}],
            ["c", "cat3", 1, {"z": 1}],
        ],
        "stock": {},
        "offers": [
            ["o1", {"x": 1, "y": 1, "z": 1}, 1, 1],
        ],
        "prep": [],
        "max_difficulty": 1,
    }


class TestTransform(unittest.TestCase):
    def test_infeasible_plan_is_null(self):
        # No offer can supply the required materials -> plan must be null.
        payload = _payload()
        payload["offers"] = []
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["dishes"], ["a", "b", "c"])
        self.assertIsNone(result[0]["plan"])

    def test_distinct_categories_required(self):
        # Two dishes share a category, so no valid triple exists -> empty output.
        payload = _payload()
        payload["dishes"] = [
            ["a", "cat1", 1, {"x": 1}],
            ["b", "cat1", 1, {"y": 1}],
            ["c", "cat2", 1, {"z": 1}],
        ]
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(result, [])

    def test_difficulty_filter(self):
        # A dish above max_difficulty is excluded, leaving fewer than 3 categories.
        payload = _payload()
        payload["dishes"] = [
            ["a", "cat1", 1, {"x": 1}],
            ["b", "cat2", 1, {"y": 1}],
            ["c", "cat3", 5, {"z": 1}],
        ]
        payload["max_difficulty"] = 2
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(result, [])

    def test_lexicographic_tie_break_cost(self):
        # Two offers both satisfy the requirement; the cheaper one must win.
        payload = _payload()
        payload["offers"] = [
            ["o1", {"x": 1, "y": 1, "z": 1}, 5, 1],
            ["o2", {"x": 1, "y": 1, "z": 1}, 2, 1],
        ]
        result = call_candidate("solution.py", "transform", args=[payload])
        plan = result[0]["plan"]
        self.assertEqual(plan["cost"], 2)
        self.assertEqual(plan["buy"], [0, 1])

    def test_left_positive_only(self):
        # Extra material beyond requirement must appear in left as positive.
        payload = _payload()
        payload["offers"] = [
            ["o1", {"x": 2, "y": 1, "z": 1}, 1, 1],
        ]
        result = call_candidate("solution.py", "transform", args=[payload])
        plan = result[0]["plan"]
        self.assertEqual(plan["left"], {"x": 1})


if __name__ == "__main__":
    unittest.main()
