import unittest

# Injected names provided by the visible-contract SDK runner.
# call_candidate(path, function, args=[...]) -> JSON value
# check_api_boundary(...) -> raises on failure
# CandidateCallError -> raised for candidate exceptions

API_BOUNDARY_REQUIREMENTS = [
    {
        "target_path": "components/scenario_prefixes/work.py",
        "function": "compute",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": False,
                "contract_path": "components/scenario_prefixes/README.md",
                "requirement_quote": "输入字段为 scenarios。缺省字段沿用原题约定。",
                "reason": "README does not state ValueError on non-finite or unknown fields.",
            },
            "invalid_payload_type": {
                "applicable": False,
                "contract_path": "components/scenario_prefixes/README.md",
                "requirement_quote": "输入字段为 scenarios。缺省字段沿用原题约定。",
                "reason": "README does not state ValueError on invalid payload type.",
            },
        },
    },
    {
        "target_path": "components/menu_eligibility/work.py",
        "function": "compute",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": False,
                "contract_path": "components/menu_eligibility/README.md",
                "requirement_quote": "输入字段为 recipes, groups, delivery。缺省字段沿用原题约定。",
                "reason": "README does not state ValueError on non-finite or unknown fields.",
            },
            "invalid_payload_type": {
                "applicable": False,
                "contract_path": "components/menu_eligibility/README.md",
                "requirement_quote": "输入字段为 recipes, groups, delivery。缺省字段沿用原题约定。",
                "reason": "README does not state ValueError on invalid payload type.",
            },
        },
    },
]


class ScenarioPrefixesTests(unittest.TestCase):
    def test_prefixes_sorted_and_weights(self):
        payload = {
            "scenarios": [
                {"signals": ["A", "B"], "weight": 2},
                {"signals": ["A", "C"], "weight": 3},
            ]
        }
        result = call_candidate(
            "components/scenario_prefixes/work.py", "compute", args=[payload]
        )
        self.assertEqual(
            result,
            [
                [["A"], None],
                [["A", "B"], 2],
                [["A", "C"], 3],
            ],
        )

    def test_single_signal_scenario(self):
        payload = {"scenarios": [{"signals": ["X"], "weight": 7}]}
        result = call_candidate(
            "components/scenario_prefixes/work.py", "compute", args=[payload]
        )
        self.assertEqual(result, [[["X"], 7]])


class MenuEligibilityTests(unittest.TestCase):
    def test_difficulty_and_allergy_filter(self):
        payload = {
            "recipes": [
                {"id": "R1", "cat": "veg", "ingredients": ["herb"], "difficulty": 5, "cost": 1},
                {"id": "R2", "cat": "veg", "ingredients": ["bean"], "difficulty": 1, "cost": 1},
                {"id": "R3", "cat": "veg", "ingredients": ["fish"], "difficulty": 1, "cost": 1},
            ],
            "groups": [["g", 1, ["fish"], ["veg"]]],
            "delivery": {"A": ["herb", "bean", "fish"]},
        }
        result = call_candidate(
            "components/menu_eligibility/work.py", "compute", args=[payload]
        )
        # R1 excluded (difficulty>4), R3 excluded (fish banned), R2 eligible.
        self.assertEqual(result, {"A": ["R2"]})

    def test_ingredient_availability(self):
        payload = {
            "recipes": [
                {"id": "R1", "cat": "veg", "ingredients": ["bean", "rice"], "difficulty": 1, "cost": 1},
                {"id": "R2", "cat": "veg", "ingredients": ["bean"], "difficulty": 1, "cost": 1},
            ],
            "groups": [["g", 1, [], ["veg"]]],
            "delivery": {"A": ["bean"]},
        }
        result = call_candidate(
            "components/menu_eligibility/work.py", "compute", args=[payload]
        )
        # R1 needs rice (unavailable), R2 eligible.
        self.assertEqual(result, {"A": ["R2"]})


class IntegrationTests(unittest.TestCase):
    def test_infeasible_budget_returns_null(self):
        payload = {
            "recipes": [
                {"id": "R1", "cat": "veg", "ingredients": ["bean"], "difficulty": 1, "cost": 10},
            ],
            "groups": [["g", 1, [], ["veg"]]],
            "delivery": {"A": ["bean"]},
            "budget": 5,
            "scenarios": [{"signals": ["A"], "weight": 1}],
        }
        left = [[["A"], 1]]
        right = {"A": ["R1"]}
        result = call_candidate(
            "integration.py", "combine", args=[payload, left, right]
        )
        self.assertEqual(result["histories"], [["A"]])
        self.assertIsNone(result["optimal"])

    def test_single_day_optimal(self):
        payload = {
            "recipes": [
                {"id": "R1", "cat": "veg", "ingredients": ["bean"], "difficulty": 1, "cost": 3},
                {"id": "R2", "cat": "veg", "ingredients": ["bean"], "difficulty": 1, "cost": 1},
            ],
            "groups": [["g", 2, [], ["veg"]]],
            "delivery": {"A": ["bean"]},
            "budget": 10,
            "scenarios": [{"signals": ["A"], "weight": 1}],
        }
        left = [[["A"], 1]]
        right = {"A": ["R1", "R2"]}
        result = call_candidate(
            "integration.py", "combine", args=[payload, left, right]
        )
        opt = result["optimal"]
        self.assertEqual(opt["floor"], 1)
        self.assertEqual(opt["utility"], 2)
        self.assertEqual(opt["cost"], 1)
        self.assertEqual(opt["menu"], ["R2"])
        self.assertEqual(opt["allowed"], [["R2"]])


if __name__ == "__main__":
    unittest.main()
