import unittest

README = "README.md"

API_BOUNDARY_REQUIREMENTS = [
    {
        "target_path": "engines/numeric/transform.py",
        "function": "transform",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": True,
                "contract_path": README,
                "requirement_quote": "未知额外字段可忽略，但其中非有限JSON仍非法。",
            },
            "invalid_payload_type": {
                "applicable": True,
                "contract_path": README,
                "requirement_quote": "仅对象/数组顶层合法；非法JSON、其他顶层类型和任意嵌套NaN/Infinity抛ValueError。",
            },
        },
    },
    {
        "target_path": "engines/category/transform.py",
        "function": "transform",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": True,
                "contract_path": README,
                "requirement_quote": "未知额外字段可忽略，但其中非有限JSON仍非法。",
            },
            "invalid_payload_type": {
                "applicable": True,
                "contract_path": README,
                "requirement_quote": "仅对象/数组顶层合法；非法JSON、其他顶层类型和任意嵌套NaN/Infinity抛ValueError。",
            },
        },
    },
    {
        "target_path": "engines/time/transform.py",
        "function": "transform",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": True,
                "contract_path": README,
                "requirement_quote": "未知额外字段可忽略，但其中非有限JSON仍非法。",
            },
            "invalid_payload_type": {
                "applicable": True,
                "contract_path": README,
                "requirement_quote": "仅对象/数组顶层合法；非法JSON、其他顶层类型和任意嵌套NaN/Infinity抛ValueError。",
            },
        },
    },
    {
        "target_path": "engines/union/transform.py",
        "function": "transform",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": True,
                "contract_path": README,
                "requirement_quote": "未知额外字段可忽略，但其中非有限JSON仍非法。",
            },
            "invalid_payload_type": {
                "applicable": True,
                "contract_path": README,
                "requirement_quote": "仅对象/数组顶层合法；非法JSON、其他顶层类型和任意嵌套NaN/Infinity抛ValueError。",
            },
        },
    },
]


class NumericTransformTests(unittest.TestCase):
    def test_numeric_all_null_group(self):
        payload = {
            "records": [
                {"id": "a", "key": "g", "value": None, "category": None, "time": None},
            ],
            "vocabulary": ["x"],
        }
        contract = {"name": "numeric", "operation": "numeric_features", "inputs": ["inputs/case.json"]}
        result = call_candidate("engines/numeric/transform.py", "transform", args=[[payload], contract])
        self.assertEqual(result["name"], "numeric")
        rows = result["result"]["rows"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["key"], "g")
        self.assertEqual(rows[0]["values"], {"count": 0, "sum": 0, "mean": None})

    def test_numeric_mean_and_sum(self):
        payload = {
            "records": [
                {"id": "a", "key": "g", "value": 2, "category": None, "time": None},
                {"id": "b", "key": "g", "value": 4, "category": None, "time": None},
            ],
            "vocabulary": [],
        }
        contract = {"name": "numeric", "operation": "numeric_features", "inputs": ["inputs/case.json"]}
        result = call_candidate("engines/numeric/transform.py", "transform", args=[[payload], contract])
        rows = result["result"]["rows"]
        self.assertEqual(rows[0]["values"], {"count": 2, "sum": 6, "mean": 3.0})


class CategoryTransformTests(unittest.TestCase):
    def test_category_all_null_group_omitted(self):
        payload = {
            "records": [
                {"id": "a", "key": "g", "value": 1, "category": None, "time": None},
            ],
            "vocabulary": ["red", "blue"],
        }
        contract = {"name": "category", "operation": "category_features", "inputs": ["inputs/case.json"]}
        result = call_candidate("engines/category/transform.py", "transform", args=[[payload], contract])
        self.assertEqual(result["result"]["rows"], [])

    def test_category_unknown_category_no_new_column(self):
        payload = {
            "records": [
                {"id": "a", "key": "g", "value": 1, "category": "other", "time": None},
            ],
            "vocabulary": ["red"],
        }
        contract = {"name": "category", "operation": "category_features", "inputs": ["inputs/case.json"]}
        result = call_candidate("engines/category/transform.py", "transform", args=[[payload], contract])
        rows = result["result"]["rows"]
        self.assertEqual(rows[0]["values"], {"red": False})


class TimeTransformTests(unittest.TestCase):
    def test_time_span_uses_min_max(self):
        payload = {
            "records": [
                {"id": "a", "key": "g", "value": 1, "category": None, "time": 10},
                {"id": "b", "key": "g", "value": 1, "category": None, "time": -5},
                {"id": "c", "key": "g", "value": 1, "category": None, "time": 3},
            ],
            "vocabulary": [],
        }
        contract = {"name": "time", "operation": "time_features", "inputs": ["inputs/case.json"]}
        result = call_candidate("engines/time/transform.py", "transform", args=[[payload], contract])
        rows = result["result"]["rows"]
        self.assertEqual(rows[0]["values"], {"first": -5, "last": 10, "span": 15})

    def test_time_all_null_omitted(self):
        payload = {
            "records": [
                {"id": "a", "key": "g", "value": 1, "category": None, "time": None},
            ],
            "vocabulary": [],
        }
        contract = {"name": "time", "operation": "time_features", "inputs": ["inputs/case.json"]}
        result = call_candidate("engines/time/transform.py", "transform", args=[[payload], contract])
        self.assertEqual(result["result"]["rows"], [])


class UnionTransformTests(unittest.TestCase):
    def test_union_outer_join_null_fill(self):
        numeric = {"name": "numeric", "result": {"rows": [{"key": "g1", "values": {"count": 1, "sum": 5, "mean": 5.0}}]}}
        category = {"name": "category", "result": {"rows": [{"key": "g2", "values": {"red": True}}]}}
        time = {"name": "time", "result": {"rows": [{"key": "g1", "values": {"first": 1, "last": 2, "span": 1}}]}}
        contract = {"name": "union", "operation": "feature_union", "inputs": ["a", "b", "c"]}
        result = call_candidate("engines/union/transform.py", "transform", args=[[numeric, category, time], contract])
        r = result["result"]
        self.assertEqual(r["index"], ["g1", "g2"])
        self.assertEqual(r["columns"], ["cat.red", "num.count", "num.mean", "num.sum", "time.first", "time.last", "time.span"])
        self.assertEqual(r["data"][0][0], None)
        self.assertEqual(r["data"][0][1], 1)
        self.assertEqual(r["data"][1][0], True)
        self.assertEqual(r["data"][1][1], None)


class ApiBoundaryTests(unittest.TestCase):
    def test_api_boundary_probes(self):
        for req in API_BOUNDARY_REQUIREMENTS:
            target = req["target_path"]
            for rule, spec in req["rules"].items():
                if not spec["applicable"]:
                    continue
                with self.subTest(target=target, rule=rule):
                    if rule == "nonfinite_unknown_field":
                        args = [[{"records": [], "vocabulary": [], "extra": 1.0}],
                                {"name": "x", "operation": "op", "inputs": ["i"]}]
                    else:
                        args = [[{"records": [], "vocabulary": []}],
                                {"name": "x", "operation": "op", "inputs": ["i"]}]
                    check_api_boundary(
                        target,
                        rule=rule,
                        contract_path=spec["contract_path"],
                        requirement_quote=spec["requirement_quote"],
                        args=args,
                    )


if __name__ == "__main__":
    unittest.main()
