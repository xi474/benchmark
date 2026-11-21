import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

API_BOUNDARY_REQUIREMENTS = [
    {
        "target_path": "solution.py",
        "function": "transform",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": False,
                "contract_path": str(ROOT / "TASK.md"),
                "requirement_quote": "验收覆盖本文正常输入域与完整交付，不要求额外NaN/Infinity防御、错误文本、代码风格或未公开兼容范围。",
                "reason": "Public spec explicitly excludes NaN/Infinity defense.",
            },
            "invalid_payload_type": {
                "applicable": False,
                "contract_path": str(ROOT / "TASK.md"),
                "requirement_quote": "验收覆盖本文正常输入域与完整交付，不要求额外NaN/Infinity防御、错误文本、代码风格或未公开兼容范围。",
                "reason": "Public spec does not require ValueError on invalid payload types.",
            },
        },
    },
]


def _load(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


class TestTransform(unittest.TestCase):
    def test_transform_returns_full_contract(self):
        payload = _load("public_input.json")
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertIsInstance(result, dict)
        for key in ("loss", "gradients", "partitions", "events"):
            self.assertIn(key, result)
        self.assertIsInstance(result["gradients"], list)
        self.assertIsInstance(result["partitions"], list)
        self.assertIsInstance(result["events"], list)

    def test_transform_does_not_mutate_input(self):
        payload = _load("public_input.json")
        before = json.dumps(payload, sort_keys=True)
        call_candidate("solution.py", "transform", args=[payload])
        after = json.dumps(payload, sort_keys=True)
        self.assertEqual(before, after)

    def test_loss_matches_hand_computed(self):
        payload = _load("public_input.json")
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertAlmostEqual(result["loss"], 0.565232731062, places=9)

    def test_gradient_shapes_match_layers(self):
        payload = _load("public_input.json")
        result = call_candidate("solution.py", "transform", args=[payload])
        layers = payload["layers"]
        self.assertEqual(len(result["gradients"]), len(layers))
        for i, layer in enumerate(layers):
            w = layer["weight"]
            b = layer["bias"]
            self.assertEqual(len(result["gradients"][i]["weight"]), len(w))
            self.assertEqual(len(result["gradients"][i]["weight"][0]), len(w[0]))
            self.assertEqual(len(result["gradients"][i]["bias"]), len(b))

    def test_partitions_cover_all_layers(self):
        payload = _load("public_input.json")
        result = call_candidate("solution.py", "transform", args=[payload])
        parts = result["partitions"]
        L = len(payload["layers"])
        self.assertEqual(parts[0]["start"], 0)
        self.assertEqual(parts[-1]["stop"], L)
        for i in range(len(parts) - 1):
            self.assertEqual(parts[i]["stop"], parts[i + 1]["start"])

    def test_events_forward_then_backward(self):
        payload = _load("public_input.json")
        result = call_candidate("solution.py", "transform", args=[payload])
        events = result["events"]
        kinds = [e["kind"] for e in events]
        self.assertIn("forward", kinds)
        self.assertIn("backward", kinds)
        first_backward = kinds.index("backward")
        self.assertTrue(all(k == "forward" for k in kinds[:first_backward]))


if __name__ == "__main__":
    unittest.main()
