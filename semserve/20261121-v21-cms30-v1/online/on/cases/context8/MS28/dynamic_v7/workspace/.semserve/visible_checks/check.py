import unittest

# Injected by the visible-contract SDK runner.
try:
    from visible_contract_check_sdk import call_candidate, CandidateCallError, check_api_boundary
except Exception:
    call_candidate = None
    CandidateCallError = Exception
    check_api_boundary = None

VISIBLE_DOC = "TASK.md"

API_BOUNDARY_REQUIREMENTS = [
    {
        "target_path": "solution.py",
        "function": "transform",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": False,
                "contract_path": VISIBLE_DOC,
                "requirement_quote": "实现 solution.py 中的 transform(payload)，返回题面指定的 JSON 值并保持输入值完整。",
                "reason": "The public spec does not state that unknown fields or non-finite values must raise ValueError.",
            },
            "invalid_payload_type": {
                "applicable": False,
                "contract_path": VISIBLE_DOC,
                "requirement_quote": "实现 solution.py 中的 transform(payload)，返回题面指定的 JSON 值并保持输入值完整。",
                "reason": "The public spec does not state that a non-object payload must raise ValueError.",
            },
        },
    },
]


class DeadlineWindowsBehavior(unittest.TestCase):
    def test_window_and_sorting(self):
        # due-7 <= day < due, original serviceable list, sorted ids.
        payload = {
            "assignments": [
                ["A", 10, 5, ["c", "a", "b"]],
                ["B", None, 9, ["a"]],
            ],
            "slots": [
                ["a", 3, 2],
                ["b", 5, 3],
                ["c", 10, 4],
            ],
        }
        expected = {
            "A": [5, ["a", "b"]],
        }
        result = call_candidate("components/deadline_windows/work.py", "compute", args=[payload])
        self.assertEqual(result, expected)


class RemainingSlotsBehavior(unittest.TestCase):
    def test_withdrawal_removal(self):
        payload = {
            "slots": [["a", 4, 2], ["b", 5, 3], ["c", 6, 4]],
            "withdrawals": [[], ["b"], ["a", "c"]],
        }
        expected = [
            {"a": [4, 2], "b": [5, 3], "c": [6, 4]},
            {"a": [4, 2], "c": [6, 4]},
            {"b": [5, 3]},
        ]
        result = call_candidate("components/remaining_slots/work.py", "compute", args=[payload])
        self.assertEqual(result, expected)


class IntegrationBehavior(unittest.TestCase):
    def test_empty_no_deadline(self):
        payload = {"assignments": [["A", None, 5, ["a"]]], "slots": [["a", 1, 2]], "withdrawals": [[]]}
        left = {}
        right = [{"a": [1, 2]}]
        result = call_candidate("integration.py", "combine", args=[payload, left, right])
        self.assertEqual(result, [{"empty": True}])

    def test_unserved(self):
        payload = {"assignments": [["A", 10, 5, ["a"]]], "slots": [["a", 1, 2]], "withdrawals": [["a"]]}
        left = {"A": [5, ["a"]]}
        right = [{}]
        result = call_candidate("integration.py", "combine", args=[payload, left, right])
        self.assertEqual(result, [{"unserved": ["A"]}])

    def test_peak_single_assignment(self):
        # One assignment, one slot: ratio 5/2.
        payload = {"assignments": [["A", 10, 5, ["a"]]], "slots": [["a", 1, 2]], "withdrawals": [[]]}
        left = {"A": [5, ["a"]]}
        right = [{"a": [1, 2]}]
        result = call_candidate("integration.py", "combine", args=[payload, left, right])
        self.assertEqual(result[0]["peak"], [5, 2])
        self.assertEqual(result[0]["count"], 1)
        self.assertEqual(result[0]["minimal"], [["A"]])
        self.assertEqual(result[0]["implies"], [["A", []]])


if __name__ == "__main__":
    unittest.main()
