import unittest

API_BOUNDARY_REQUIREMENTS = [
    {
        "target_path": "transform.py",
        "function": "transform",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": True,
                "contract_path": "README.md",
                "requirement_quote": "未知额外字段可忽略，但其中非有限JSON仍非法",
            },
            "invalid_payload_type": {
                "applicable": True,
                "contract_path": "README.md",
                "requirement_quote": "仅对象/数组顶层合法；非法JSON、其他顶层类型和任意嵌套NaN/Infinity抛ValueError",
            },
        },
    },
    {
        "target_path": "domains/schema/transform.py",
        "function": "transform",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": True,
                "contract_path": "README.md",
                "requirement_quote": "未知额外字段可忽略，但其中非有限JSON仍非法",
            },
            "invalid_payload_type": {
                "applicable": True,
                "contract_path": "README.md",
                "requirement_quote": "仅对象/数组顶层合法；非法JSON、其他顶层类型和任意嵌套NaN/Infinity抛ValueError",
            },
        },
    },
    {
        "target_path": "domains/attachments/transform.py",
        "function": "transform",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": True,
                "contract_path": "README.md",
                "requirement_quote": "未知额外字段可忽略，但其中非有限JSON仍非法",
            },
            "invalid_payload_type": {
                "applicable": True,
                "contract_path": "README.md",
                "requirement_quote": "仅对象/数组顶层合法；非法JSON、其他顶层类型和任意嵌套NaN/Infinity抛ValueError",
            },
        },
    },
    {
        "target_path": "views/references/transform.py",
        "function": "transform",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": True,
                "contract_path": "README.md",
                "requirement_quote": "未知额外字段可忽略，但其中非有限JSON仍非法",
            },
            "invalid_payload_type": {
                "applicable": True,
                "contract_path": "README.md",
                "requirement_quote": "仅对象/数组顶层合法；非法JSON、其他顶层类型和任意嵌套NaN/Infinity抛ValueError",
            },
        },
    },
    {
        "target_path": "views/snapshot/transform.py",
        "function": "transform",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": True,
                "contract_path": "README.md",
                "requirement_quote": "未知额外字段可忽略，但其中非有限JSON仍非法",
            },
            "invalid_payload_type": {
                "applicable": True,
                "contract_path": "README.md",
                "requirement_quote": "仅对象/数组顶层合法；非法JSON、其他顶层类型和任意嵌套NaN/Infinity抛ValueError",
            },
        },
    },
]


def _payload():
    return {
        "flags": [
            {
                "id": "f",
                "variants": [{"id": "v", "attachment": {"x": 1}}],
                "rules": [{"id": "r", "segment": "s", "variant": "v"}],
            }
        ],
        "segments": [{"id": "s"}],
    }


class TestTransformBoundaries(unittest.TestCase):
    def test_nonfinite_unknown_field(self):
        contract = {"name": "schema", "operation": "feature_schema", "inputs": ["x"], "output": "y"}
        check_api_boundary(
            "transform.py",
            rule="nonfinite_unknown_field",
            contract_path="README.md",
            requirement_quote="未知额外字段可忽略，但其中非有限JSON仍非法",
            args=[[_payload()], contract],
        )

    def test_invalid_payload_type(self):
        contract = {"name": "schema", "operation": "feature_schema", "inputs": ["x"], "output": "y"}
        check_api_boundary(
            "transform.py",
            rule="invalid_payload_type",
            contract_path="README.md",
            requirement_quote="仅对象/数组顶层合法；非法JSON、其他顶层类型和任意嵌套NaN/Infinity抛ValueError",
            args=[[_payload()], contract],
        )

    def test_schema_result_shape(self):
        payload = _payload()
        contract = {"name": "schema", "operation": "feature_schema", "inputs": ["x"], "output": "y"}
        result = call_candidate("transform.py", "transform", args=[[payload], contract])
        self.assertEqual(set(result), {"name", "result"})
        self.assertEqual(result["name"], "schema")
        self.assertEqual(set(result["result"]), {"flags", "segments"})
        self.assertEqual(result["result"]["flags"], payload["flags"])
        self.assertEqual(result["result"]["segments"], payload["segments"])

    def test_references_missing_segment(self):
        payload = _payload()
        payload["flags"][0]["rules"][0]["segment"] = "missing"
        contract = {"name": "references", "operation": "feature_references", "inputs": ["x"], "output": "y"}
        result = call_candidate("transform.py", "transform", args=[[payload], contract])
        self.assertEqual(result["result"]["ok"], False)
        self.assertEqual(result["result"]["error"]["kind"], "segment")
        self.assertEqual(result["result"]["error"]["flag"], "f")
        self.assertEqual(result["result"]["error"]["rule"], "r")
        self.assertEqual(result["result"]["error"]["target"], "missing")

    def test_references_missing_variant(self):
        payload = _payload()
        payload["flags"][0]["rules"][0]["variant"] = "missing"
        contract = {"name": "references", "operation": "feature_references", "inputs": ["x"], "output": "y"}
        result = call_candidate("transform.py", "transform", args=[[payload], contract])
        self.assertEqual(result["result"]["ok"], False)
        self.assertEqual(result["result"]["error"]["kind"], "variant")
        self.assertEqual(result["result"]["error"]["flag"], "f")
        self.assertEqual(result["result"]["error"]["rule"], "r")
        self.assertEqual(result["result"]["error"]["target"], "missing")

    def test_attachments_canonical(self):
        payload = _payload()
        payload["flags"][0]["variants"][0]["attachment"] = {"b": 2, "a": [1, None, True]}
        contract = {"name": "attachments", "operation": "feature_attachments", "inputs": ["x"], "output": "y"}
        result = call_candidate("transform.py", "transform", args=[[payload], contract])
        entry = result["result"]["attachments"]["f"]["v"]
        self.assertEqual(entry["value"], {"b": 2, "a": [1, None, True]})
        self.assertEqual(entry["canonical"], '{"a":[1,null,true],"b":2}')

    def test_shim_boundaries(self):
        contract = {"name": "schema", "operation": "feature_schema", "inputs": ["x"], "output": "y"}
        for target in [
            "domains/schema/transform.py",
            "domains/attachments/transform.py",
            "views/references/transform.py",
            "views/snapshot/transform.py",
        ]:
            with self.subTest(target=target):
                check_api_boundary(
                    target,
                    rule="invalid_payload_type",
                    contract_path="README.md",
                    requirement_quote="仅对象/数组顶层合法；非法JSON、其他顶层类型和任意嵌套NaN/Infinity抛ValueError",
                    args=[[_payload()], contract],
                )
                check_api_boundary(
                    target,
                    rule="nonfinite_unknown_field",
                    contract_path="README.md",
                    requirement_quote="未知额外字段可忽略，但其中非有限JSON仍非法",
                    args=[[_payload()], contract],
                )


if __name__ == "__main__":
    unittest.main()
