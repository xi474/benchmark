import unittest

# Injected names available at runtime.
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
                "reason": "The visible contract does not state that transform must reject non-finite values or unknown fields.",
            },
            "invalid_payload_type": {
                "applicable": False,
                "contract_path": VISIBLE_DOC,
                "requirement_quote": "实现 solution.py 中的 transform(payload)，返回题面指定的 JSON 值并保持输入值完整。",
                "reason": "The visible contract does not state that transform must raise ValueError on invalid payload types.",
            },
        },
    },
]


class TestTransformBehavior(unittest.TestCase):
    def test_public_fixture_roundtrip(self):
        # Output contract: list of per-query dicts with incidents and repairs.
        payload = {
            "domains": ["a", "b", "c", "d", "e"],
            "services": [
                {"id": "ledger", "need": 2, "inputs": ["a", "b", "c"]},
                {"id": "orders", "need": 1, "inputs": ["a", "d"]},
                {"id": "mail", "need": 2, "inputs": ["orders", "ledger", "e"]},
            ],
            "log": [
                ["b", 2, 8, "degraded"],
                ["a", 0, 1, "down"],
                ["a", 4, 5, "down"],
                ["c", 0, 1, "up"],
                ["a", 2, 3, "up"],
                ["a", 0, 7, "up"],
                ["c", 4, 5, "down"],
                ["b", 4, 5, "degraded"],
                ["e", 4, 5, "up"],
                ["d", 2, 3, "up"],
                ["e", 0, 1, "degraded"],
                ["b", 2, 3, "degraded"],
                ["d", 4, 5, "down"],
                ["a", 2, 9, "down"],
                ["c", 2, 3, "up"],
                ["b", 0, 1, "degraded"],
                ["d", 0, 1, "up"],
                ["e", 2, 3, "down"],
            ],
            "queries": [
                {"start": 0, "end": 5, "as_of": 6, "targets": ["mail", "ledger"]},
                {"start": 1, "end": 6, "as_of": 9, "targets": ["mail", "ledger"]},
            ],
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)
        for item in result:
            self.assertIsInstance(item, dict)
            self.assertIn("incidents", item)
            self.assertIn("repairs", item)

    def test_no_repair_needed_returns_empty_set(self):
        # All domains up, single target domain -> no incidents, repairs [[]].
        payload = {
            "domains": ["a", "b"],
            "services": [],
            "log": [["a", 0, 1, "up"], ["b", 0, 1, "up"]],
            "queries": [{"start": 0, "end": 2, "as_of": 5, "targets": ["a"]}],
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(result[0]["incidents"], [])
        self.assertEqual(result[0]["repairs"], [[]])

    def test_single_domain_down_incident(self):
        # Domain a down for whole window -> incident [a, 0, 2], repair [["a"]].
        payload = {
            "domains": ["a", "b"],
            "services": [],
            "log": [["a", 0, 1, "down"], ["b", 0, 1, "up"]],
            "queries": [{"start": 0, "end": 2, "as_of": 5, "targets": ["a"]}],
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(result[0]["incidents"], [["a", 0, 2]])
        self.assertEqual(result[0]["repairs"], [["a"]])

    def test_service_quorum_requires_two_inputs(self):
        # Service s needs 2 of {a, b}. a down, b up -> s unavailable.
        payload = {
            "domains": ["a", "b"],
            "services": [{"id": "s", "need": 2, "inputs": ["a", "b"]}],
            "log": [["a", 0, 1, "down"], ["b", 0, 1, "up"]],
            "queries": [{"start": 0, "end": 2, "as_of": 5, "targets": ["s"]}],
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(result[0]["incidents"], [["s", 0, 2]])
        self.assertEqual(result[0]["repairs"], [["a"]])

    def test_as_of_filters_later_records(self):
        # A later record (seen after as_of) must not be visible.
        payload = {
            "domains": ["a"],
            "services": [],
            "log": [["a", 0, 1, "down"], ["a", 0, 9, "up"]],
            "queries": [{"start": 0, "end": 2, "as_of": 5, "targets": ["a"]}],
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(result[0]["incidents"], [["a", 0, 2]])


if __name__ == "__main__":
    unittest.main()
