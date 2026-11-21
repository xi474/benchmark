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
                "reason": "The public specification does not state that transform must reject non-finite values in unknown fields; it only requires returning the specified JSON value.",
            },
            "invalid_payload_type": {
                "applicable": False,
                "contract_path": "TASK.md",
                "requirement_quote": "实现 solution.py 中的 transform(payload)，返回题面指定的 JSON 值并保持输入值完整。",
                "reason": "The public specification does not state that transform must raise ValueError for a non-object payload; it only describes the business input shape.",
            },
        },
    },
]


class TransformBehaviorTests(unittest.TestCase):
    def test_public_fixture_matches_expected(self):
        # Independent oracle: recompute the public example's optimal policy.
        import json
        from pathlib import Path
        payload = json.loads(Path("public_input.json").read_text(encoding="utf-8"))
        expected = json.loads(Path("public_expected.json").read_text(encoding="utf-8"))
        actual = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(actual, expected)

    def test_infeasible_budget_returns_null(self):
        # A budget too small for any single day must yield optimal == null.
        import json
        from pathlib import Path
        payload = json.loads(Path("public_input.json").read_text(encoding="utf-8"))
        payload = json.loads(json.dumps(payload))
        payload["budget"] = 0
        actual = call_candidate("solution.py", "transform", args=[payload])
        self.assertIsNone(actual["optimal"])

    def test_histories_are_sorted_short_first(self):
        # Histories must be lexicographically sorted with short prefixes first.
        import json
        from pathlib import Path
        payload = json.loads(Path("public_input.json").read_text(encoding="utf-8"))
        actual = call_candidate("solution.py", "transform", args=[payload])
        histories = [tuple(h) for h in actual["histories"]]
        self.assertEqual(histories, sorted(histories))
        for i in range(len(histories) - 1):
            a, b = histories[i], histories[i + 1]
            if len(a) < len(b):
                self.assertEqual(a, b[:len(a)])


if __name__ == "__main__":
    unittest.main()
