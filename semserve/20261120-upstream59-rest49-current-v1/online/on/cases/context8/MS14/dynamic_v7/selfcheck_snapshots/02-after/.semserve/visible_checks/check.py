import unittest

# Injected by the SDK runner; do not import.
# call_candidate(path, function, args=[...]) -> JSON value
# check_api_boundary(...) -> raises on failure
# CandidateCallError -> candidate exception wrapper

API_BOUNDARY_REQUIREMENTS = [
    {
        "target_path": "solution.py",
        "function": "transform",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": False,
                "contract_path": "TASK.md",
                "requirement_quote": "实现 solution.py 中的 transform(payload)，返回题面指定的 JSON 值并保持输入值完整。",
                "reason": "The public spec does not state that unknown fields or non-finite values must raise ValueError; it only requires returning the specified JSON value.",
            },
            "invalid_payload_type": {
                "applicable": False,
                "contract_path": "TASK.md",
                "requirement_quote": "实现 solution.py 中的 transform(payload)，返回题面指定的 JSON 值并保持输入值完整。",
                "reason": "The public spec does not document a ValueError contract for non-object payloads.",
            },
        },
    },
]


class TransformBehaviorTests(unittest.TestCase):
    def test_public_example_matches_expected(self):
        # Independent re-derivation of the public example output.
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
        expected = [
            {
                "incidents": [
                    ["ledger", 0, 2],
                    ["ledger", 4, 5],
                    ["mail", 0, 2],
                    ["mail", 4, 5],
                ],
                "repairs": [["a", "b"], ["a", "c"], ["b", "c"]],
            },
            {
                "incidents": [
                    ["ledger", 2, 6],
                    ["mail", 2, 6],
                ],
                "repairs": [["a", "b"], ["a", "c"], ["b", "c"]],
            },
        ]
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(result, expected)

    def test_no_repair_needed_returns_empty_set(self):
        # All domains up, single service with need 1 -> no incidents, repairs [[]].
        payload = {
            "domains": ["a"],
            "services": [{"id": "s", "need": 1, "inputs": ["a"]}],
            "log": [],
            "queries": [{"start": 0, "end": 3, "as_of": 10, "targets": ["s"]}],
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(result, [{"incidents": [], "repairs": [[]]}])

    def test_domain_down_requires_repair(self):
        # Domain a down for the whole window; target is the domain itself.
        payload = {
            "domains": ["a"],
            "services": [],
            "log": [["a", 0, 1, "down"]],
            "queries": [{"start": 0, "end": 2, "as_of": 10, "targets": ["a"]}],
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(
            result,
            [{"incidents": [["a", 0, 2]], "repairs": [["a"]]}],
        )

    def test_need_threshold_distinct_inputs(self):
        # Service needs 2 of 3 inputs; only one is up -> unavailable.
        payload = {
            "domains": ["a", "b", "c"],
            "services": [{"id": "s", "need": 2, "inputs": ["a", "b", "c"]}],
            "log": [
                ["a", 0, 1, "down"],
                ["b", 0, 1, "down"],
            ],
            "queries": [{"start": 0, "end": 2, "as_of": 10, "targets": ["s"]}],
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        # a and b down, c up -> only 1 available, need 2 -> incident [0,2).
        # Minimal repair: fix a or b (either gives 2 available).
        self.assertEqual(
            result,
            [{"incidents": [["s", 0, 2]], "repairs": [["a"], ["b"]]}],
        )

    def test_as_of_filters_future_records(self):
        # A record with record_time > as_of must be ignored.
        payload = {
            "domains": ["a"],
            "services": [],
            "log": [["a", 0, 5, "down"]],
            "queries": [{"start": 0, "end": 2, "as_of": 4, "targets": ["a"]}],
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        # record_time 5 > as_of 4 -> ignored -> a stays up.
        self.assertEqual(result, [{"incidents": [], "repairs": [[]]}])

    def test_same_effective_time_last_record_wins(self):
        # Two records same effective time; last recorded version wins.
        payload = {
            "domains": ["a"],
            "services": [],
            "log": [
                ["a", 0, 1, "down"],
                ["a", 0, 2, "up"],
            ],
            "queries": [{"start": 0, "end": 2, "as_of": 10, "targets": ["a"]}],
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        # effective 0: last record (rec 2) is "up" -> no incident.
        self.assertEqual(result, [{"incidents": [], "repairs": [[]]}])


if __name__ == "__main__":
    unittest.main()
