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
                "contract_path": "TASK.md",
                "requirement_quote": "所有数量、价格均为非负整数，并且每个报价的价格为正。",
                "reason": "TASK.md does not state that transform must raise ValueError on unknown fields or non-finite values; it only constrains business input values.",
            },
            "invalid_payload_type": {
                "applicable": False,
                "contract_path": "TASK.md",
                "requirement_quote": "实现 solution.py 中的 transform(payload)，返回题面指定的 JSON 值并保持输入值完整。",
                "reason": "TASK.md does not specify a ValueError contract for non-object payloads; it only describes the JSON return value.",
            },
        },
    },
]


def _load(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class TestDishRequirements(unittest.TestCase):
    def test_qualified_triples_and_merge(self):
        # Public rule: three dishes, distinct categories, difficulty <= max,
        # merged same-name material quantities summed, sorted by dish ID.
        payload = _load("components/dish_requirements/input.json")
        result = call_candidate("components/dish_requirements/work.py", "compute", args=[payload])
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0][0], ["bread", "chips", "soup"])
        self.assertEqual(result[0][1], {"flour": 2, "peel": 1, "mash": 1})
        self.assertEqual(result[1][0], ["chips", "pie", "soup"])
        self.assertEqual(result[1][1], {"peel": 1, "flour": 1, "mash": 2})


class TestPurchaseBaskets(unittest.TestCase):
    def test_basket_enumeration_and_order(self):
        # Public rule: all limited baskets [cost, count, buy vector] sorted by
        # (cost, count, vector).
        payload = _load("components/purchase_baskets/input.json")
        result = call_candidate("components/purchase_baskets/work.py", "compute", args=[payload])
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 12)
        keys = [(b[0], b[1], tuple(b[2])) for b in result]
        self.assertEqual(keys, sorted(keys))
        self.assertEqual(result[0], [0, 0, [0, 0, 0]])
        self.assertEqual(result[1], [2, 1, [0, 0, 1]])


class TestIntegration(unittest.TestCase):
    def test_public_plan_optimality(self):
        # Public rule: minimize cost, then buy count, then buy vector, then
        # total steps, then step ID sequence.
        payload = _load("public_input.json")
        left = call_candidate(
            "components/dish_requirements/work.py", "compute",
            args=[{"dishes": payload["dishes"], "max_difficulty": payload["max_difficulty"]}],
        )
        right = call_candidate(
            "components/purchase_baskets/work.py", "compute",
            args=[{"offers": payload["offers"]}],
        )
        result = call_candidate("integration.py", "combine", args=[payload, left, right])
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)
        first = result[0]
        self.assertEqual(first["dishes"], ["bread", "chips", "soup"])
        self.assertEqual(first["plan"]["cost"], 3)
        self.assertEqual(first["plan"]["buy"], [0, 1, 0])
        self.assertEqual(first["plan"]["steps"], ["mill", "pare"])
        self.assertEqual(first["plan"]["left"], {})

    def test_infeasible_plan_is_null(self):
        # Public rule: no feasible purchase/prep plan -> plan is null.
        payload = _load("public_input.json")
        payload = dict(payload)
        payload["offers"] = []
        left = call_candidate(
            "components/dish_requirements/work.py", "compute",
            args=[{"dishes": payload["dishes"], "max_difficulty": payload["max_difficulty"]}],
        )
        right = call_candidate(
            "components/purchase_baskets/work.py", "compute",
            args=[{"offers": payload["offers"]}],
        )
        result = call_candidate("integration.py", "combine", args=[payload, left, right])
        for entry in result:
            self.assertIsNone(entry["plan"])


if __name__ == "__main__":
    unittest.main()
