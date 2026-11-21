import unittest

# Runtime injects call_candidate, CandidateCallError, check_api_boundary into
# this module's globals before execution. They are used directly, no import.

API_BOUNDARY_REQUIREMENTS = [
    {
        "target_path": "solution.py",
        "function": "transform",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": True,
                "contract_path": "TASK.md",
                "requirement_quote": "实现 solution.py 中的 transform(payload)，返回题面指定的 JSON 值并保持输入值完整。",
            },
            "invalid_payload_type": {
                "applicable": True,
                "contract_path": "TASK.md",
                "requirement_quote": "实现 solution.py 中的 transform(payload)，返回题面指定的 JSON 值并保持输入值完整。",
            },
        },
    },
]


def _payload():
    return {
        "students": ["S1", "S2"],
        "buyers": ["B1", "B2"],
        "grades": [
            ["S1", 1, 50],
            ["S1", 2, 50],
            ["S2", 1, 40],
            ["S2", 2, 40],
        ],
        "orders": [
            {"buyer": "B1", "status": "done", "lines": [[["Electronics"], 1, 10]]},
            {"buyer": "B2", "status": "done", "lines": [[["Cameras"], 1, 20]]},
        ],
        "evidence": [
            ["src", "S1", "B1", 5],
            ["src", "S2", "B2", 5],
        ],
        "drop": [None],
    }


class TransformBehaviorTests(unittest.TestCase):
    def test_output_shape_and_forced_pairs(self):
        # Independent small case: unique perfect matching, forced pairs present.
        payload = _payload()
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        item = result[0]
        self.assertIsNone(item["drop"])
        r = item["result"]
        self.assertIsNotNone(r)
        self.assertEqual(r["count"], 1)
        self.assertEqual(r["floor"], 5)
        self.assertEqual(r["total"], 10)
        # X: S1=5000, S2=4000; Y: B1=10, B2=20; n=2
        # sxy = 5000*10 + 4000*20 = 130000; sx=9000; sy=30
        # num = 2*130000 - 9000*30 = 260000 - 270000 = -10000
        self.assertEqual(r["min_num"], -10000)
        self.assertEqual(r["max_num"], -10000)
        self.assertEqual(r["min_buyers"], ["B1", "B2"])
        self.assertEqual(r["max_buyers"], ["B1", "B2"])
        self.assertEqual(r["forced"], [["S1", "B1"], ["S2", "B2"]])

    def test_drop_removes_source_and_yields_null(self):
        # Dropping the only source leaves no evidence -> no complete mapping.
        payload = _payload()
        payload["drop"] = ["src"]
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["drop"], "src")
        self.assertIsNone(result[0]["result"])

    def test_input_not_mutated(self):
        payload = _payload()
        before = repr(payload)
        call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(repr(payload), before)

    def test_api_boundary_nonfinite_unknown_field(self):
        check_api_boundary(
            "solution.py",
            rule="nonfinite_unknown_field",
            contract_path="TASK.md",
            requirement_quote="实现 solution.py 中的 transform(payload)，返回题面指定的 JSON 值并保持输入值完整。",
            args=[_payload(), {}],
        )

    def test_api_boundary_invalid_payload_type(self):
        check_api_boundary(
            "solution.py",
            rule="invalid_payload_type",
            contract_path="TASK.md",
            requirement_quote="实现 solution.py 中的 transform(payload)，返回题面指定的 JSON 值并保持输入值完整。",
            args=[_payload(), {}],
        )


if __name__ == "__main__":
    unittest.main()
