import unittest

API_BOUNDARY_REQUIREMENTS = [
    {
        "target_path": "dinner/transform.py",
        "function": "transform",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": True,
                "contract_path": "README.md",
                "requirement_quote": "必需字段缺失、指定非法类型/重复/冲突均ValueError。整数排除bool，有限数允许int/float但排除bool及非有限数",
                "args": [
                    [{"today": "2026-11-04", "weekday": 5, "hour": 19, "guest_count": 6}],
                    {"name": "dinner", "operation": "dinner_date", "inputs": ["x"], "output": "y"},
                ],
            },
            "invalid_payload_type": {
                "applicable": True,
                "contract_path": "README.md",
                "requirement_quote": "仅对象/数组顶层合法；非法JSON、其他顶层类型和任意嵌套NaN/Infinity抛ValueError",
                "args": [
                    [{"today": "2026-11-04", "weekday": 5, "hour": 19, "guest_count": 6}],
                    {"name": "dinner", "operation": "dinner_date", "inputs": ["x"], "output": "y"},
                ],
            },
        },
    },
    {
        "target_path": "contact/transform.py",
        "function": "transform",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": True,
                "contract_path": "README.md",
                "requirement_quote": "必需字段缺失、指定非法类型/重复/冲突均ValueError。整数排除bool，有限数允许int/float但排除bool及非有限数",
                "args": [
                    [{"topic": "dinner", "conversations": [{"id": "a", "contact_id": "c1", "ts": 5, "topic": "Dinner"}]}],
                    {"name": "contact", "operation": "recent_contact", "inputs": ["x"], "output": "y"},
                ],
            },
            "invalid_payload_type": {
                "applicable": True,
                "contract_path": "README.md",
                "requirement_quote": "仅对象/数组顶层合法；非法JSON、其他顶层类型和任意嵌套NaN/Infinity抛ValueError",
                "args": [
                    [{"topic": "dinner", "conversations": [{"id": "a", "contact_id": "c1", "ts": 5, "topic": "Dinner"}]}],
                    {"name": "contact", "operation": "recent_contact", "inputs": ["x"], "output": "y"},
                ],
            },
        },
    },
    {
        "target_path": "shopping/transform.py",
        "function": "transform",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": True,
                "contract_path": "README.md",
                "requirement_quote": "必需字段缺失、指定非法类型/重复/冲突均ValueError。整数排除bool，有限数允许int/float但排除bool及非有限数",
                "args": [
                    [
                        {"variants": [{"id": "v0", "kind": "cup", "attributes": {"c": "w"}, "stock": 5, "price_cents": 10}], "wanted": [{"kind": "cup", "attributes": {"c": "w"}}]},
                        {"start": "2026-11-07T19:00", "guest_count": 2},
                        {"contact_id": "c1", "conversation_id": "a"},
                    ],
                    {"name": "shopping", "operation": "dinner_checkout", "inputs": ["a", "b", "c"], "output": "y"},
                ],
            },
            "invalid_payload_type": {
                "applicable": True,
                "contract_path": "README.md",
                "requirement_quote": "仅对象/数组顶层合法；非法JSON、其他顶层类型和任意嵌套NaN/Infinity抛ValueError",
                "args": [
                    [
                        {"variants": [{"id": "v0", "kind": "cup", "attributes": {"c": "w"}, "stock": 5, "price_cents": 10}], "wanted": [{"kind": "cup", "attributes": {"c": "w"}}]},
                        {"start": "2026-11-07T19:00", "guest_count": 2},
                        {"contact_id": "c1", "conversation_id": "a"},
                    ],
                    {"name": "shopping", "operation": "dinner_checkout", "inputs": ["a", "b", "c"], "output": "y"},
                ],
            },
        },
    },
]


class TestDinner(unittest.TestCase):
    def test_dinner_date_next_weekday(self):
        payload = {
            "today": "2026-11-04",
            "weekday": 5,
            "hour": 19,
            "guest_count": 6,
        }
        contract = {"name": "dinner", "operation": "dinner_date", "inputs": ["x"], "output": "y"}
        result = call_candidate("dinner/transform.py", "transform", args=[[payload], contract])
        self.assertEqual(result["name"], "dinner")
        self.assertEqual(result["result"], {"start": "2026-11-07T19:00", "guest_count": 6})

    def test_dinner_same_weekday_adds_seven(self):
        payload = {
            "today": "2026-11-04",
            "weekday": 2,
            "hour": 0,
            "guest_count": 1,
        }
        contract = {"name": "dinner", "operation": "dinner_date", "inputs": ["x"], "output": "y"}
        result = call_candidate("dinner/transform.py", "transform", args=[[payload], contract])
        self.assertEqual(result["result"]["start"], "2026-11-11T00:00")

    def test_dinner_bool_weekday_rejected(self):
        payload = {
            "today": "2026-11-04",
            "weekday": True,
            "hour": 19,
            "guest_count": 6,
        }
        contract = {"name": "dinner", "operation": "dinner_date", "inputs": ["x"], "output": "y"}
        with self.assertRaises(CandidateCallError) as cm:
            call_candidate("dinner/transform.py", "transform", args=[[payload], contract])
        self.assertEqual(cm.exception.details["failure_phase"], "candidate_exception")
        self.assertEqual(cm.exception.details["error_type"], "ValueError")


class TestContact(unittest.TestCase):
    def test_contact_latest_ts_tiebreak(self):
        payload = {
            "topic": "dinner",
            "conversations": [
                {"id": "a", "contact_id": "c1", "ts": 5, "topic": "Dinner"},
                {"id": "b", "contact_id": "c2", "ts": 5, "topic": "Dinner"},
                {"id": "c", "contact_id": "c3", "ts": 3, "topic": "Dinner"},
            ],
        }
        contract = {"name": "contact", "operation": "recent_contact", "inputs": ["x"], "output": "y"}
        result = call_candidate("contact/transform.py", "transform", args=[[payload], contract])
        self.assertEqual(result["result"], {"contact_id": "c1", "conversation_id": "a"})

    def test_contact_no_match_null(self):
        payload = {
            "topic": "dinner",
            "conversations": [
                {"id": "a", "contact_id": "c1", "ts": 5, "topic": "Lunch"},
            ],
        }
        contract = {"name": "contact", "operation": "recent_contact", "inputs": ["x"], "output": "y"}
        result = call_candidate("contact/transform.py", "transform", args=[[payload], contract])
        self.assertEqual(result["result"], {"contact_id": None, "conversation_id": None})


class TestShopping(unittest.TestCase):
    def test_shopping_unavailable_and_no_checkout(self):
        snapshot = {
            "variants": [
                {"id": "v0", "kind": "cup", "attributes": {"c": "w"}, "stock": 1, "price_cents": 10},
            ],
            "wanted": [
                {"kind": "cup", "attributes": {"c": "w"}},
                {"kind": "plate", "attributes": {"c": "w"}},
            ],
        }
        dinner = {"start": "2026-11-07T19:00", "guest_count": 2}
        contact = {"contact_id": "c1", "conversation_id": "a"}
        contract = {"name": "shopping", "operation": "dinner_checkout", "inputs": ["a", "b", "c"], "output": "y"}
        result = call_candidate("shopping/transform.py", "transform", args=[[snapshot, dinner, contact], contract])
        r = result["result"]
        self.assertEqual(r["checkout"], False)
        self.assertEqual(r["unavailable"], ["cup", "plate"])
        self.assertEqual(r["items"], [])
        self.assertEqual(r["recipient"], "c1")

    def test_shopping_lowest_price_then_id(self):
        snapshot = {
            "variants": [
                {"id": "z", "kind": "cup", "attributes": {"c": "w"}, "stock": 5, "price_cents": 20},
                {"id": "a", "kind": "cup", "attributes": {"c": "w"}, "stock": 5, "price_cents": 20},
                {"id": "m", "kind": "cup", "attributes": {"c": "w"}, "stock": 5, "price_cents": 10},
            ],
            "wanted": [{"kind": "cup", "attributes": {"c": "w"}}],
        }
        dinner = {"start": "2026-11-07T19:00", "guest_count": 2}
        contact = {"contact_id": "c1", "conversation_id": "a"}
        contract = {"name": "shopping", "operation": "dinner_checkout", "inputs": ["a", "b", "c"], "output": "y"}
        result = call_candidate("shopping/transform.py", "transform", args=[[snapshot, dinner, contact], contract])
        r = result["result"]
        self.assertEqual(r["items"], [{"id": "m", "kind": "cup", "quantity": 2}])
        self.assertEqual(r["total_cents"], 20)
        self.assertEqual(r["checkout"], True)


class TestApiBoundaries(unittest.TestCase):
    def test_api_boundaries(self):
        for entry in API_BOUNDARY_REQUIREMENTS:
            for rule, spec in entry["rules"].items():
                if not spec.get("applicable", False):
                    continue
                with self.subTest(target=entry["target_path"], rule=rule):
                    check_api_boundary(
                        entry["target_path"],
                        rule=rule,
                        contract_path=spec["contract_path"],
                        requirement_quote=spec["requirement_quote"],
                        args=spec["args"],
                    )


if __name__ == "__main__":
    unittest.main()
