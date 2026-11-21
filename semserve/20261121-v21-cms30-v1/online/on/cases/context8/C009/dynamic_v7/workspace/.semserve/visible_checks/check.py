import unittest

# Injected names (no import needed).
# call_candidate(path, function, args=[...]) -> JSON value
# CandidateCallError with details["failure_phase"], details["error_type"]
# check_api_boundary(...)

VISIBLE_DOC = "TASK.md"


class TestTransformBehavior(unittest.TestCase):
    def test_output_shape_and_rounds(self):
        payload = {
            "vehicles": [{"id": "v1", "type": "bulk", "capacity": 3, "cost": 1}],
            "drivers": [{"id": "d1", "types": ["bulk"], "max_work": 4,
                         "max_continuous": 2, "break": 1}],
            "suppliers": [{"id": "s1", "stock": 4, "close": 5, "unit_cost": 2}],
            "events": [],
            "rounds": [{"cutoff": 1, "commit": True}],
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertIsInstance(result, dict)
        self.assertIn("rounds", result)
        self.assertEqual(len(result["rounds"]), 1)
        r = result["rounds"][0]
        self.assertEqual(r["cutoff"], 1)
        self.assertEqual(r["assignments"], [])
        self.assertEqual(r["profit"], 0)
        self.assertEqual(r["cancelled"], [])
        self.assertEqual(r["ignored_cancellations"], [])

    def test_single_job_assignment(self):
        payload = {
            "vehicles": [{"id": "v1", "type": "bulk", "capacity": 3, "cost": 1}],
            "drivers": [{"id": "d1", "types": ["bulk"], "max_work": 10,
                         "max_continuous": 10, "break": 1}],
            "suppliers": [{"id": "s1", "stock": 10, "close": 10, "unit_cost": 2}],
            "events": [{"id": "e1", "visible": 1, "kind": "request",
                        "job": {"id": "j1", "type": "bulk", "quantity": 2,
                                "release": 1, "deadline": 5, "duration": 2,
                                "revenue": 20, "suppliers": ["s1"]}}],
            "rounds": [{"cutoff": 1, "commit": True}],
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        r = result["rounds"][0]
        self.assertEqual(len(r["assignments"]), 1)
        a = r["assignments"][0]
        self.assertEqual(a["job"], "j1")
        self.assertEqual(a["vehicle"], "v1")
        self.assertEqual(a["driver"], "d1")
        self.assertEqual(a["supplier"], "s1")
        self.assertEqual(a["start"], 1)
        self.assertEqual(a["end"], 3)
        self.assertEqual(a["quantity"], 2)
        # profit = 20 - 2*2 - 1*2 = 14
        self.assertEqual(a["profit"], 14)
        self.assertEqual(r["profit"], 14)

    def test_cancel_uncommitted_job(self):
        payload = {
            "vehicles": [{"id": "v1", "type": "bulk", "capacity": 3, "cost": 1}],
            "drivers": [{"id": "d1", "types": ["bulk"], "max_work": 10,
                         "max_continuous": 10, "break": 1}],
            "suppliers": [{"id": "s1", "stock": 10, "close": 10, "unit_cost": 2}],
            "events": [
                {"id": "e1", "visible": 1, "kind": "request",
                 "job": {"id": "j1", "type": "bulk", "quantity": 2,
                         "release": 1, "deadline": 5, "duration": 2,
                         "revenue": 20, "suppliers": ["s1"]}},
                {"id": "e2", "visible": 2, "kind": "cancel", "job": "j1"},
            ],
            "rounds": [{"cutoff": 1, "commit": False},
                       {"cutoff": 2, "commit": True}],
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        r = result["rounds"][1]
        self.assertEqual(r["assignments"], [])
        self.assertEqual(r["cancelled"], ["j1"])
        self.assertEqual(r["ignored_cancellations"], [])

    def test_cancel_committed_started_job_ignored(self):
        payload = {
            "vehicles": [{"id": "v1", "type": "bulk", "capacity": 3, "cost": 1}],
            "drivers": [{"id": "d1", "types": ["bulk"], "max_work": 10,
                         "max_continuous": 10, "break": 1}],
            "suppliers": [{"id": "s1", "stock": 10, "close": 10, "unit_cost": 2}],
            "events": [
                {"id": "e1", "visible": 1, "kind": "request",
                 "job": {"id": "j1", "type": "bulk", "quantity": 2,
                         "release": 1, "deadline": 5, "duration": 2,
                         "revenue": 20, "suppliers": ["s1"]}},
                {"id": "e2", "visible": 3, "kind": "cancel", "job": "j1"},
            ],
            "rounds": [{"cutoff": 1, "commit": True},
                       {"cutoff": 3, "commit": True}],
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        r = result["rounds"][1]
        self.assertEqual(len(r["assignments"]), 1)
        self.assertEqual(r["cancelled"], [])
        self.assertEqual(r["ignored_cancellations"], ["j1"])


if __name__ == "__main__":
    unittest.main()
