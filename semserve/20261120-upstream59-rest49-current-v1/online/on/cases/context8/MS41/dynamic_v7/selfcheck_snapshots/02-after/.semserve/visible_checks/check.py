import unittest
import json
from fractions import Fraction


def call_candidate(path, function, args):
    # Local shim for direct invocation in this self-check environment.
    import importlib.util
    spec = importlib.util.spec_from_file_location("candidate_mod", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    fn = getattr(mod, function)
    return fn(*args)


class CandidateCallError(Exception):
    def __init__(self, details):
        self.details = details
        super().__init__(str(details))


class TestTransform(unittest.TestCase):

    def _run(self, payload):
        return call_candidate("/workspace/solution.py", "transform", [payload])

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
        # Sorted by correct prob desc: vote (20/27) before direct (2/3).
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
        # One version, one state, single edge to answer A with cost 5.
        payload = {
            "answers": ["A", "B"],
            "correct": "A",
            "profiles": {"v": 1},
            "methods": [
                {"id": "m", "votes": 1, "start": "s",
                 "graphs": {"v": {"s": [["A", 1, 5]]}}},
            ],
        }
        result = self._run(payload)
        self.assertEqual(len(result), 1)
        r = result[0]
        self.assertEqual(r["prob"], [[1, 1], [0, 1]])
        self.assertEqual(r["unresolved"], [0, 1])
        self.assertEqual(r["launches"], [1, 1])
        self.assertEqual(r["cost_if_correct"], [5, 1])

    def test_unresolved_loop(self):
        # A state that loops forever never yields an answer.
        payload = {
            "answers": ["A"],
            "correct": "A",
            "profiles": {"v": 1},
            "methods": [
                {"id": "m", "votes": 3, "start": "s",
                 "graphs": {"v": {"s": [["s", 1, 0]]}}},
            ],
        }
        result = self._run(payload)
        r = result[0]
        self.assertEqual(r["prob"], [[0, 1]])
        self.assertEqual(r["unresolved"], [1, 1])
        self.assertEqual(r["launches"], [1, 1])
        self.assertIsNone(r["cost_if_correct"])

    def test_cost_if_correct_null_when_correct_impossible(self):
        # Correct answer B never produced; cost_if_correct must be null.
        payload = {
            "answers": ["A", "B"],
            "correct": "B",
            "profiles": {"v": 1},
            "methods": [
                {"id": "m", "votes": 2, "start": "s",
                 "graphs": {"v": {"s": [["A", 1, 2]]}}},
            ],
        }
        result = self._run(payload)
        r = result[0]
        self.assertEqual(r["prob"], [[1, 1], [0, 1]])
        self.assertIsNone(r["cost_if_correct"])

    def test_version_weighting(self):
        # Two versions with weights 1 and 3; answer A prob = (1*1 + 3*0)/4 = 1/4.
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
        result = self._run(payload)
        r = result[0]
        self.assertEqual(r["prob"], [[1, 4], [3, 4]])
        self.assertEqual(r["cost_if_correct"], [0, 1])

    def test_tie_break_earlier_answer(self):
        # Two votes, each yields A or B with prob 1/2. With 2 votes, ties go to A.
        payload = {
            "answers": ["A", "B"],
            "correct": "A",
            "profiles": {"v": 1},
            "methods": [
                {"id": "m", "votes": 2, "start": "s",
                 "graphs": {"v": {"s": [["A", 1, 0], ["B", 1, 0]]}}},
            ],
        }
        result = self._run(payload)
        r = result[0]
        # Outcomes: AA, AB, BA, BB each 1/4. Winner A for AA, AB, BA (tie->A),
        # B only for BB. So prob A = 3/4, B = 1/4.
        self.assertEqual(r["prob"], [[3, 4], [1, 4]])

    def test_launches_early_stop(self):
        # votes=3, but first vote decides (deterministic A). launches must be 1.
        payload = {
            "answers": ["A", "B"],
            "correct": "A",
            "profiles": {"v": 1},
            "methods": [
                {"id": "m", "votes": 3, "start": "s",
                 "graphs": {"v": {"s": [["A", 1, 0]]}}},
            ],
        }
        result = self._run(payload)
        r = result[0]
        self.assertEqual(r["launches"], [1, 1])


if __name__ == "__main__":
    unittest.main()
