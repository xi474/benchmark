"""Bounded visible-contract self-checks for solution.py.

These tests exercise the public business contract in TASK.md beyond the
public fixture.  They use the Runtime-injected call_candidate and
check_api_boundary helpers (no import needed).
"""

import unittest

# The public transform API takes a single payload object.  The visible
# contract (TASK.md) does not document ValueError behavior for non-finite
# values in unknown fields, nor for a non-object payload; those inputs are
# outside the stated normal input domain, so the boundary rules are not
# applicable here.
API_BOUNDARY_REQUIREMENTS = [
    {
        "target_path": "solution.py",
        "function": "transform",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": False,
                "contract_path": "TASK.md",
                "requirement_quote": "验收覆盖本文正常输入域与完整交付，不要求额外NaN/Infinity防御、错误文本、代码风格或未公开兼容范围。",
                "reason": "The visible contract explicitly excludes NaN/Infinity defense and unspecified compatibility ranges.",
            },
            "invalid_payload_type": {
                "applicable": False,
                "contract_path": "TASK.md",
                "requirement_quote": "验收覆盖本文正常输入域与完整交付，不要求额外NaN/Infinity防御、错误文本、代码风格或未公开兼容范围。",
                "reason": "The visible contract does not require ValueError for a non-object payload; only the normal input domain is covered.",
            },
        },
    },
]


class TransformContractTests(unittest.TestCase):
    """Independent invariants derived from TASK.md."""

    def test_loss_and_gradients_match_public_fixture(self):
        # Public fixture: world_size=1, two layers, one microbatch.
        payload = {
            "world_size": 1,
            "layers": [
                {"weight": [[-0.428571, -0.142857], [0.0, 0.285714],
                            [0.428571, -0.285714]],
                 "bias": [0.0, 0.076923, 0.153846]},
                {"weight": [[-0.285714, 0.0, 0.285714],
                            [0.142857, 0.428571, -0.285714]],
                 "bias": [-0.076923, 0.0]},
            ],
            "microbatches": [
                {"inputs": [[1.0, -2.0], [0.5, 0.7]], "targets": [0, 1]},
            ],
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertAlmostEqual(result["loss"], 0.565232731062, places=9)
        self.assertEqual(len(result["gradients"]), 2)
        self.assertEqual(len(result["partitions"]), 1)
        self.assertEqual(result["partitions"][0],
                         {"stage": 0, "start": 0, "stop": 2})
        self.assertEqual(result["events"],
                         [{"kind": "forward", "microbatch": 0, "stage": 0},
                          {"kind": "backward", "microbatch": 0, "stage": 0}])

    def test_input_not_mutated(self):
        payload = {
            "world_size": 1,
            "layers": [
                {"weight": [[1.0, 0.0], [0.0, 1.0]], "bias": [0.0, 0.0]},
            ],
            "microbatches": [
                {"inputs": [[1.0, 2.0]], "targets": [0]},
            ],
        }
        import copy
        before = copy.deepcopy(payload)
        call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(payload, before)

    def test_world_size_two_partitions_and_events(self):
        # Three layers, world_size=2 -> stage0 owns layer0, stage1 owns 1..2.
        payload = {
            "world_size": 2,
            "layers": [
                {"weight": [[1.0, 0.0], [0.0, 1.0]], "bias": [0.0, 0.0]},
                {"weight": [[1.0, 0.0], [0.0, 1.0]], "bias": [0.0, 0.0]},
                {"weight": [[1.0, 0.0], [0.0, 1.0]], "bias": [0.0, 0.0]},
            ],
            "microbatches": [
                {"inputs": [[1.0, 2.0]], "targets": [0]},
            ],
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(result["partitions"],
                         [{"stage": 0, "start": 0, "stop": 1},
                          {"stage": 1, "start": 1, "stop": 3}])
        kinds = [e["kind"] for e in result["events"]]
        self.assertEqual(kinds, ["forward", "forward", "send_activation",
                                  "backward", "backward", "send_gradient"])

    def test_gradients_shape_matches_layers(self):
        payload = {
            "world_size": 1,
            "layers": [
                {"weight": [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]],
                 "bias": [0.0, 0.0]},
                {"weight": [[1.0, 0.0], [0.0, 1.0]], "bias": [0.0, 0.0]},
            ],
            "microbatches": [
                {"inputs": [[1.0, 2.0, 3.0]], "targets": [0]},
            ],
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(len(result["gradients"]), 2)
        self.assertEqual(len(result["gradients"][0]["weight"]), 2)
        self.assertEqual(len(result["gradients"][0]["weight"][0]), 3)
        self.assertEqual(len(result["gradients"][0]["bias"]), 2)
        self.assertEqual(len(result["gradients"][1]["weight"]), 2)
        self.assertEqual(len(result["gradients"][1]["weight"][0]), 2)
        self.assertEqual(len(result["gradients"][1]["bias"]), 2)


if __name__ == "__main__":
    unittest.main()
