import json
import unittest
from pathlib import Path

API_BOUNDARY_REQUIREMENTS = [
    {
        "target_path": "component_runtime.py",
        "function": "transform",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": False,
                "contract_path": "TASK.md",
                "requirement_quote": "实现 solution.py 中的 transform(payload)，返回题面指定的 JSON 值并保持输入值完整。",
                "reason": "The public spec does not state that non-finite values in unknown fields must raise ValueError.",
            },
            "invalid_payload_type": {
                "applicable": False,
                "contract_path": "TASK.md",
                "requirement_quote": "实现 solution.py 中的 transform(payload)，返回题面指定的 JSON 值并保持输入值完整。",
                "reason": "The public spec does not state that a non-object payload must raise ValueError.",
            },
        },
    },
]


class TransformBehaviorTests(unittest.TestCase):
    def test_public_fixture_output(self):
        payload = json.loads(Path("public_input.json").read_text(encoding="utf-8"))
        expected = json.loads(Path("public_expected.json").read_text(encoding="utf-8"))
        actual = call_candidate("component_runtime.py", "transform", args=[payload])
        self.assertEqual(actual, expected)

    def test_infeasible_snapshot_returns_null(self):
        payload = {
            "snapshots": [
                {
                    "ab": [[1, 0], [0, 0]],
                    "bc": [[0, 0], [0, 0]],
                    "ac": [[0, 0], [0, 0]],
                    "forbidden": [],
                }
            ]
        }
        actual = call_candidate("component_runtime.py", "transform", args=[payload])
        self.assertEqual(actual, [None])

    def test_forbidden_cell_removes_table(self):
        payload = {
            "snapshots": [
                {
                    "ab": [[1, 0], [0, 0]],
                    "bc": [[1, 0], [0, 0]],
                    "ac": [[1, 0], [0, 0]],
                    "forbidden": [[0, 0, 0]],
                }
            ]
        }
        actual = call_candidate("component_runtime.py", "transform", args=[payload])
        self.assertEqual(actual, [None])


if __name__ == "__main__":
    unittest.main()
