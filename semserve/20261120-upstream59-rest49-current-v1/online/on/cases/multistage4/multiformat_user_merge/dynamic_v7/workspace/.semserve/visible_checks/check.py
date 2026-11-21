import unittest

API_BOUNDARY_REQUIREMENTS = [
    {
        "target_path": "domains/json_users/transform.py",
        "function": "transform",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": True,
                "contract_path": "README.md",
                "requirement_quote": "任意嵌套NaN/Infinity抛ValueError",
            },
            "invalid_payload_type": {
                "applicable": True,
                "contract_path": "README.md",
                "requirement_quote": "仅对象/数组顶层合法；非法JSON、其他顶层类型和任意嵌套NaN/Infinity抛ValueError",
            },
        },
    },
    {
        "target_path": "domains/csv_users/transform.py",
        "function": "transform",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": True,
                "contract_path": "README.md",
                "requirement_quote": "任意嵌套NaN/Infinity抛ValueError",
            },
            "invalid_payload_type": {
                "applicable": True,
                "contract_path": "README.md",
                "requirement_quote": "仅对象/数组顶层合法；非法JSON、其他顶层类型和任意嵌套NaN/Infinity抛ValueError",
            },
        },
    },
    {
        "target_path": "domains/jsonl_users/transform.py",
        "function": "transform",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": True,
                "contract_path": "README.md",
                "requirement_quote": "任意嵌套NaN/Infinity抛ValueError",
            },
            "invalid_payload_type": {
                "applicable": True,
                "contract_path": "README.md",
                "requirement_quote": "仅对象/数组顶层合法；非法JSON、其他顶层类型和任意嵌套NaN/Infinity抛ValueError",
            },
        },
    },
    {
        "target_path": "views/directory/transform.py",
        "function": "transform",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": True,
                "contract_path": "README.md",
                "requirement_quote": "任意嵌套NaN/Infinity抛ValueError",
            },
            "invalid_payload_type": {
                "applicable": True,
                "contract_path": "README.md",
                "requirement_quote": "仅对象/数组顶层合法；非法JSON、其他顶层类型和任意嵌套NaN/Infinity抛ValueError",
            },
        },
    },
]


class TestJsonUsers(unittest.TestCase):
    def test_records_sorted_and_normalized(self):
        payload = {"json_text": '[{"id": 2, "name": "B", "joined": "03/01/2024"}, {"id": 1, "email": "a@b"}]'}
        contract = {"name": "json_users", "inputs": ["x"]}
        out = call_candidate("domains/json_users/transform.py", "transform", args=[[payload], contract])
        self.assertEqual(out["name"], "json_users")
        records = out["result"]["records"]
        self.assertEqual([r["id"] for r in records], ["1", "2"])
        self.assertEqual(records[1]["joined"], "2024-01-03")
        self.assertNotIn("joined", records[0])

    def test_duplicate_id_last_value_wins(self):
        payload = {"json_text": '[{"id": 1, "name": "A"}, {"id": 1, "name": "B"}]'}
        contract = {"name": "json_users", "inputs": ["x"]}
        out = call_candidate("domains/json_users/transform.py", "transform", args=[[payload], contract])
        self.assertEqual(out["result"]["records"][0]["name"], "B")


class TestDirectory(unittest.TestCase):
    def test_merge_priority_and_conflicts(self):
        json_rec = {"name": "json_users", "result": {"records": [{"id": "1", "name": "J", "email": "j@x"}]}}
        csv_rec = {"name": "csv_users", "result": {"records": [{"id": "1", "name": "C", "email": "c@x"}]}}
        jsonl_rec = {"name": "jsonl_users", "result": {"records": [{"id": "2", "name": "L"}]}}
        contract = {"name": "directory", "inputs": ["a", "b", "c"]}
        out = call_candidate("views/directory/transform.py", "transform", args=[[json_rec, csv_rec, jsonl_rec], contract])
        users = {u["id"]: u for u in out["result"]["users"]}
        self.assertEqual(users["1"]["name"], "J")
        self.assertEqual(users["1"]["email"], "j@x")
        self.assertIn("2", users)
        conflicts = {(c["id"], c["field"]): c for c in out["result"]["conflicts"]}
        self.assertIn(("1", "name"), conflicts)
        self.assertIn(("1", "email"), conflicts)


class TestApiBoundary(unittest.TestCase):
    def test_boundary_probes(self):
        seeds = {
            "domains/json_users/transform.py": [{"json_text": '[{"id": 1}]'}, {"name": "json_users", "inputs": ["x"]}],
            "domains/csv_users/transform.py": [{"csv_text": "id,name\n1,A\n"}, {"name": "csv_users", "inputs": ["x"]}],
            "domains/jsonl_users/transform.py": [{"jsonl_text": '{"id": 1}\n'}, {"name": "jsonl_users", "inputs": ["x"]}],
            "views/directory/transform.py": [
                [
                    {"name": "json_users", "result": {"records": [{"id": "1"}]}},
                    {"name": "csv_users", "result": {"records": []}},
                    {"name": "jsonl_users", "result": {"records": []}},
                ],
                {"name": "directory", "inputs": ["a", "b", "c"]},
            ],
        }
        for req in API_BOUNDARY_REQUIREMENTS:
            target = req["target_path"]
            for rule, spec in req["rules"].items():
                if not spec.get("applicable"):
                    continue
                with self.subTest(target=target, rule=rule):
                    check_api_boundary(
                        target, rule=rule,
                        contract_path=spec["contract_path"],
                        requirement_quote=spec["requirement_quote"],
                        args=seeds[target],
                    )


if __name__ == "__main__":
    unittest.main()
