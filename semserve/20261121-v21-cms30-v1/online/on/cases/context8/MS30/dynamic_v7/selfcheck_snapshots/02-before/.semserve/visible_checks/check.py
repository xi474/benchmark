import unittest

API_BOUNDARY_REQUIREMENTS = [
    {
        "target_path": "components/student_tiers/work.py",
        "function": "compute",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": False,
                "contract_path": "components/student_tiers/README.md",
                "requirement_quote": "使用 16、17 号课程非空成绩的精确分数比，按原门槛输出学生到 P/D/N 层级映射。",
                "reason": "The public contract does not state that unknown fields or non-finite values must raise ValueError.",
            },
            "invalid_payload_type": {
                "applicable": False,
                "contract_path": "components/student_tiers/README.md",
                "requirement_quote": "输入字段为 grades。缺省字段沿用原题约定。",
                "reason": "The public contract does not state that a non-object payload must raise ValueError.",
            },
        },
    },
    {
        "target_path": "components/market_ranking/work.py",
        "function": "compute",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": False,
                "contract_path": "components/market_ranking/README.md",
                "requirement_quote": "按最新市场日的 30 天窗口、相对绝对涨跌幅和代号打破平局，返回前 top 个房间代号（保持排名）。",
                "reason": "The public contract does not state that unknown fields or non-finite values must raise ValueError.",
            },
            "invalid_payload_type": {
                "applicable": False,
                "contract_path": "components/market_ranking/README.md",
                "requirement_quote": "输入字段为 market, top。缺省字段沿用原题约定。",
                "reason": "The public contract does not state that a non-object payload must raise ValueError.",
            },
        },
    },
]


class StudentTiersBehavior(unittest.TestCase):
    def test_tier_thresholds_and_average(self):
        payload = {
            "grades": [
                ["A", 16, 5, 10], ["A", 17, 10, 16],
                ["B", 16, 6, 10], ["B", 17, 9, 16],
                ["C", 16, 7, 10], ["C", 17, 8, 16],
                ["D", 16, 8, 10], ["D", 17, 7, 16],
            ]
        }
        result = call_candidate("components/student_tiers/work.py", "compute", args=[payload])
        self.assertEqual(result, {"A": "N", "B": "N", "C": "D", "D": "D"})

    def test_ignores_other_courses_and_null(self):
        payload = {
            "grades": [
                ["A", 16, 8, 10],
                ["A", 15, 0, 10],
                ["A", 17, None, 16],
            ]
        }
        result = call_candidate("components/student_tiers/work.py", "compute", args=[payload])
        self.assertEqual(result, {"A": "P"})


class MarketRankingBehavior(unittest.TestCase):
    def test_window_and_tiebreak(self):
        payload = {
            "market": [
                ["J", 100, 100, 120],
                ["K", 91, 100, 80],
                ["L", 82, 100, 120],
                ["M", 73, 100, 80],
            ],
            "top": 3,
        }
        result = call_candidate("components/market_ranking/work.py", "compute", args=[payload])
        self.assertEqual(result, ["J", "K", "L"])

    def test_window_excludes_old_events(self):
        payload = {
            "market": [
                ["A", 100, 100, 200],
                ["B", 70, 100, 200],
            ],
            "top": 2,
        }
        result = call_candidate("components/market_ranking/work.py", "compute", args=[payload])
        self.assertEqual(result, ["A"])


class IntegrationBehavior(unittest.TestCase):
    def test_combine_public_scenario(self):
        payload = {
            "rooms": {
                "J": {"capacity": 1, "tiers": [["P"], ["D", "N"]]},
                "K": {"capacity": 2, "tiers": [["N", "D"], ["P"]]},
                "L": {"capacity": 1, "tiers": [["P"], ["D", "N"]]},
                "M": {"capacity": 2, "tiers": [["N", "D"], ["P"]]},
            },
            "prefs": {
                "A": [["J", "M"], ["L", "K"]],
                "B": [["J", "L"], ["M", "K"]],
                "C": [["J", "K"], ["L", "M"]],
                "D": [["M", "L"], ["K", "J"]],
            },
            "cancel": [[], ["J"], ["K", "L"]],
        }
        left = {"A": "N", "B": "N", "C": "D", "D": "D"}
        right = ["J", "K", "L"]
        result = call_candidate("integration.py", "combine", args=[payload, left, right])
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0]["sizes"], [[4, 12]])
        self.assertEqual(result[0]["forced"], [])
        self.assertEqual(result[0]["example"], ["J", "K", "K", "L"])
        self.assertEqual(result[2]["forced"], [])
        self.assertEqual(result[2]["example"], ["", "", "", "J"])


if __name__ == "__main__":
    unittest.main()
