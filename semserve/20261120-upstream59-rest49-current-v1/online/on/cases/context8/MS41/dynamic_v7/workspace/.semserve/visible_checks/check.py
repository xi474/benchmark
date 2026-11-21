import unittest
import json
from fractions import Fraction


class TestTransform(unittest.TestCase):

    def _run(self, payload):
        return call_candidate("solution.py", "transform", args=[payload])

    def test_public_fixture_matches_expected(self):
        payload = {
            "answers": ["A", "B"],
            "correct": "A",
            "profiles": {"standard": 1},
            "methods": [
                {"id": "direct", "votes": 1, "start": "entry",
                 "graphs": {"standard": {"entry": [["A", 2, 1], ["B", 1, 3]]}}},
                {"id": "vote", "votes": 3, "start": "entry",
                 "graphs": {"standard": {"entry": [["A", 2, 1], ["B", 1, 3]]}}},
            ],
        }
        result = self._run(payload)
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)
        self.assertEqual([r["id"] for r in result], ["vote", "direct"])
        vote = result[0]
        self.assertEqual(vote["prob"], [[20, 27], [7, 27]])
        self.assertEqual(vote["unresolved"], [0, 1])
        self.assertEqual(vote["launches"], [22, 9])
        self.assertEqual(vote["cost_if_correct"], [16, 5])
        direct = result[1]
        self.assertEqual(direct["prob"], [[2, 3], [1, 3]])
        self.assertEqual(direct["unresolved"], [0, 1])
        self.assertEqual(direct["launches"], [1, 1])
        self.assertEqual(direct["cost_if_correct"], [1, 1])

    def test_single_vote_deterministic_answer(self):
        payload = {
            "answers": ["A", "B"],
            "correct": "A",
            "profiles": {"v": 1},
            "methods": [
                {"id": "m", "votes": 1, "start": "s",
                 "graphs": {"v": {"s": [["A", 1, 5]]}}},
            ],
        }
        r = self._run(payload)[0]
        self.assertEqual(r["prob"], [[1, 1], [0, 1]])
        self.assertEqual(r["unresolved"], [0, 1])
        self.assertEqual(r["launches"], [1, 1])
        self.assertEqual(r["cost_if_correct"], [5, 1])

    def test_unresolved_loop(self):
        payload = {
            "answers": ["A"],
            "correct": "A",
            "profiles": {"v": 1},
            "methods": [
                {"id": "m", "votes": 3, "start": "s",
                 "graphs": {"v": {"s": [["s", 1, 0]]}}},
            ],
        }
        r = self._run(payload)[0]
        self.assertEqual(r["prob"], [[0, 1]])
        self.assertEqual(r["unresolved"], [1, 1])
        self.assertEqual(r["launches"], [1, 1])
        self.assertIsNone(r["cost_if_correct"])

    def test_cost_if_correct_null_when_correct_impossible(self):
        payload = {
            "answers": ["A", "B"],
            "correct": "B",
            "profiles": {"v": 1},
            "methods": [
                {"id": "m", "votes": 2, "start": "s",
                 "graphs": {"v": {"s": [["A", 1, 2]]}}},
            ],
        }
        r = self._run(payload)[0]
        self.assertEqual(r["prob"], [[1, 1], [0, 1]])
        self.assertIsNone(r["cost_if_correct"])

    def test_version_weighting(self):
        payload = {
            "answers": ["A", "B"],
            "correct": "A",
            "profiles": {"v1": 1, "v2": 3},
            "methods": [
                {"id": "m", "votes": 1, "start": "s",
                 "graphs": {
                     "v1": {"s": [["A", 1, 0]]},
                     "v2": {"s": [["B", 1, 0]]},
                 }},
            ],
        }
        r = self._run(payload)[0]
        self.assertEqual(r["prob"], [[1, 4], [3, 4]])
        self.assertEqual(r["cost_if_correct"], [0, 1])

    def test_tie_break_earlier_answer(self):
        payload = {
            "answers": ["A", "B"],
            "correct": "A",
            "profiles": {"v": 1},
            "methods": [
                {"id": "m", "votes": 2, "start": "s",
                 "graphs": {"v": {"s": [["A", 1, 0], ["B", 1, 0]]}}},
            ],
        }
        r = self._run(payload)[0]
        self.assertEqual(r["prob"], [[3, 4], [1, 4]])

    def test_launches_early_stop(self):
        # votes=3, deterministic A. After 1 vote A=1,B=0, remaining=2:
        # B could reach 2 > 1, so cannot declare. After 2nd vote A=2,B=0,
        # remaining=1: B reaches at most 1, tie 2=2 -> A wins (earlier).
        # So exactly 2 launches.
        payload = {
            "answers": ["A", "B"],
            "correct": "A",
            "profiles": {"v": 1},
            "methods": [
                {"id": "m", "votes": 3, "start": "s",
                 "graphs": {"v": {"s": [["A", 1, 0]]}}},
            ],
        }
        r = self._run(payload)[0]
        self.assertEqual(r["launches"], [2, 1])


if __name__ == "__main__":
    unittest.main()
