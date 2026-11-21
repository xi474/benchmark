import unittest
import json
from pathlib import Path

TASK = Path(__file__).resolve().parents[2] / "TASK.md"
PUBLIC_INPUT = Path(__file__).resolve().parents[2] / "public_input.json"
PUBLIC_EXPECTED = Path(__file__).resolve().parents[2] / "public_expected.json"

API_BOUNDARY_REQUIREMENTS = [
    {
        "target_path": "solution.py",
        "function": "transform",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": False,
                "contract_path": str(TASK),
                "requirement_quote": "实现 solution.py 中的 transform(payload)，返回题面指定的 JSON 值并保持输入值完整。",
                "reason": "The visible contract does not state that non-finite numeric values must raise ValueError.",
            },
            "invalid_payload_type": {
                "applicable": False,
                "contract_path": str(TASK),
                "requirement_quote": "实现 solution.py 中的 transform(payload)，返回题面指定的 JSON 值并保持输入值完整。",
                "reason": "The visible contract does not state that a non-object payload must raise ValueError.",
            },
        },
    },
]


class TestTransform(unittest.TestCase):
    def test_public_matches_expected(self):
        payload = json.loads(PUBLIC_INPUT.read_text(encoding="utf-8"))
        expected = json.loads(PUBLIC_EXPECTED.read_text(encoding="utf-8"))
        actual = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(actual, expected)

    def test_empty_no_due_assignments(self):
        payload = {
            "assignments": [["A", None, 5, ["s1"]]],
            "slots": [["s1", 3, 10]],
            "withdrawals": [[], ["s1"]],
        }
        actual = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(actual, [{"empty": True}, {"empty": True}])

    def test_unserved_sorted(self):
        payload = {
            "assignments": [
                ["B", 10, 2, ["s1"]],
                ["A", 10, 3, ["s2"]],
            ],
            "slots": [
                ["s1", 5, 10],
                ["s2", 5, 10],
            ],
            "withdrawals": [["s1", "s2"]],
        }
        actual = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(actual, [{"unserved": ["A", "B"]}])

    def test_single_assignment_peak(self):
        payload = {
            "assignments": [["A", 10, 6, ["s1"]]],
            "slots": [["s1", 5, 4]],
            "withdrawals": [[]],
        }
        actual = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(actual[0]["peak"], [3, 2])
        self.assertEqual(actual[0]["count"], 1)
        self.assertEqual(actual[0]["minimal"], [["A"]])
        self.assertEqual(actual[0]["implies"], [["A", []]])

    def test_window_boundary(self):
        payload = {
            "assignments": [["A", 10, 5, ["s1", "s2"]]],
            "slots": [
                ["s1", 3, 10],
                ["s2", 10, 10],
            ],
            "withdrawals": [[]],
        }
        actual = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(actual[0]["peak"], [1, 2])

    def test_peak_can_be_less_than_one(self):
        payload = {
            "assignments": [["A", 10, 2, ["s1"]]],
            "slots": [["s1", 5, 8]],
            "withdrawals": [[]],
        }
        actual = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(actual[0]["peak"], [1, 4])


if __name__ == "__main__":
    unittest.main()
