import unittest

# Injected by the SDK runner; do not import.
# call_candidate(path, function, args=[...]) -> JSON value
# CandidateCallError for candidate exceptions.

API_BOUNDARY_REQUIREMENTS = [
    {
        "target_path": "solution.py",
        "function": "transform",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": False,
                "contract_path": "TASK.md",
                "requirement_quote": "实现 solution.py 中的 transform(payload)，返回题面指定的 JSON 值并保持输入值完整。",
                "reason": "The public spec does not state that unknown fields or non-finite values must raise ValueError; it only defines the business computation.",
            },
            "invalid_payload_type": {
                "applicable": False,
                "contract_path": "TASK.md",
                "requirement_quote": "实现 solution.py 中的 transform(payload)，返回题面指定的 JSON 值并保持输入值完整。",
                "reason": "The public spec does not declare a ValueError contract for non-object payloads.",
            },
        },
    },
]


class TestTransformBehavior(unittest.TestCase):
    def test_public_fixture_matches_expected(self):
        # Output contract: raw container type, per-scenario fields, ordering.
        payload = {
            "grades": [
                ["A", 16, 5, 10], ["B", 16, 6, 10], ["C", 16, 7, 10],
                ["D", 16, 8, 10], ["A", 17, 10, 16], ["B", 17, 9, 16],
                ["C", 17, 8, 16], ["D", 17, 7, 16],
            ],
            "market": [
                ["J", 100, 100, 120], ["K", 91, 100, 80],
                ["L", 82, 100, 120], ["M", 73, 100, 80],
            ],
            "rooms": {
                "J": {"capacity": 1, "tiers": [["P"], ["D", "N"]]},
                "K": {"capacity": 2, "tiers": [["N", "D"], ["P"]]},
                "L": {"capacity": 1, "tiers": [["P"], ["D", "N"]]},
                "M": {"capacity": 2, "tiers": [["N", "D"], ["P"]]},
            },
            "prefs": {
                "A": [["J", "M"], ["L", "K"]],
                "B": [["J", "L"], ["M", "K"]],
                "C": [["J", "K"], ["L", "M"]],
                "D": [["M", "L"], ["K", "J"]],
            },
            "top": 3,
            "cancel": [[], ["J"], ["K", "L"]],
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 3)
        for item in result:
            self.assertIsInstance(item, dict)
            self.assertIn("sizes", item)
            self.assertIn("forced", item)
            self.assertIn("example", item)
        # First scenario: 4 students, 12 stable matchings.
        self.assertEqual(result[0]["sizes"], [[4, 12]])
        self.assertEqual(result[0]["forced"], [])
        self.assertEqual(result[0]["example"], ["J", "K", "K", "L"])

    def test_grade_boundaries(self):
        # Grade letter thresholds: <0.60 N, <0.75 D, else P.
        payload = {
            "grades": [
                ["a", 16, 59, 100], ["b", 16, 60, 100], ["c", 16, 74, 100],
                ["d", 16, 75, 100],
            ],
            "market": [["E", 10, 100, 100]],
            "rooms": {"E": {"capacity": 4, "tiers": [["N"], ["D"], ["P"]]}},
            "prefs": {
                "a": [["E"]], "b": [["E"]], "c": [["E"]], "d": [["E"]],
            },
            "top": 1,
            "cancel": [[]],
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        # All four students acceptable (tiers list all letters), capacity 4.
        self.assertEqual(result[0]["sizes"], [[4, 1]])
        # example vector sorted by student id: a,b,c,d -> all "E"
        self.assertEqual(result[0]["example"], ["E", "E", "E", "E"])

    def test_cancel_removes_event_no_refill(self):
        # Cancelling an event removes it; no backfill from the ranking.
        payload = {
            "grades": [["s", 16, 80, 100]],
            "market": [
                ["X", 100, 100, 200], ["Y", 99, 100, 150], ["Z", 98, 100, 100],
            ],
            "rooms": {
                "X": {"capacity": 1, "tiers": [["P"]]},
                "Y": {"capacity": 1, "tiers": [["P"]]},
                "Z": {"capacity": 1, "tiers": [["P"]]},
            },
            "prefs": {"s": [["X"], ["Y"], ["Z"]]},
            "top": 2,
            "cancel": [[], ["X"]],
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        # top 2 = X, Y. Cancel X leaves only Y (Z not backfilled).
        self.assertEqual(result[0]["example"], ["X"])
        self.assertEqual(result[1]["example"], ["Y"])

    def test_zero_capacity_no_blocking(self):
        # Zero-capacity event cannot form a blocking pair.
        payload = {
            "grades": [["s", 16, 80, 100]],
            "market": [["A", 10, 100, 200], ["B", 9, 100, 150]],
            "rooms": {
                "A": {"capacity": 0, "tiers": [["P"]]},
                "B": {"capacity": 1, "tiers": [["P"]]},
            },
            "prefs": {"s": [["A"], ["B"]]},
            "top": 2,
            "cancel": [[]],
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        # Student prefers A (capacity 0) but cannot block; B is acceptable.
        # Unassigned is worse than any acceptable event, so the only stable
        # matching assigns the student to B (the sole open, acceptable event).
        self.assertEqual(result[0]["sizes"], [[1, 1]])
        self.assertEqual(result[0]["forced"], [["s", "B"]])
        self.assertEqual(result[0]["example"], ["B"])


if __name__ == "__main__":
    unittest.main()
