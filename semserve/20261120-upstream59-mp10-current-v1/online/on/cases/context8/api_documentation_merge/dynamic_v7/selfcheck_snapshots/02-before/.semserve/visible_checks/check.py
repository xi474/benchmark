import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
README = "README.md"

API_BOUNDARY_REQUIREMENTS = [
    {
        "target_path": "signatures/transform.py",
        "function": "transform",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": True,
                "contract_path": README,
                "requirement_quote": "未知额外字段可忽略，但其中非有限JSON仍非法",
            },
            "invalid_payload_type": {
                "applicable": True,
                "contract_path": README,
                "requirement_quote": "仅对象/数组顶层合法；非法JSON、其他顶层类型和任意嵌套NaN/Infinity抛ValueError",
            },
        },
    },
    {
        "target_path": "parameters/transform.py",
        "function": "transform",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": True,
                "contract_path": README,
                "requirement_quote": "未知额外字段可忽略，但其中非有限JSON仍非法",
            },
            "invalid_payload_type": {
                "applicable": True,
                "contract_path": README,
                "requirement_quote": "仅对象/数组顶层合法；非法JSON、其他顶层类型和任意嵌套NaN/Infinity抛ValueError",
            },
        },
    },
    {
        "target_path": "inheritance/transform.py",
        "function": "transform",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": True,
                "contract_path": README,
                "requirement_quote": "未知额外字段可忽略，但其中非有限JSON仍非法",
            },
            "invalid_payload_type": {
                "applicable": True,
                "contract_path": README,
                "requirement_quote": "仅对象/数组顶层合法；非法JSON、其他顶层类型和任意嵌套NaN/Infinity抛ValueError",
            },
        },
    },
    {
        "target_path": "document/transform.py",
        "function": "transform",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": True,
                "contract_path": README,
                "requirement_quote": "未知额外字段可忽略，但其中非有限JSON仍非法",
            },
            "invalid_payload_type": {
                "applicable": True,
                "contract_path": README,
                "requirement_quote": "仅对象/数组顶层合法；非法JSON、其他顶层类型和任意嵌套NaN/Infinity抛ValueError",
            },
        },
    },
]


class TestApiBoundary(unittest.TestCase):
    def test_signatures_boundary(self):
        contract = {"name": "signatures", "operation": "overload_signatures", "inputs": ["in.json"], "output": "out.json"}
        payload = {"overloads": ["f(x: int) -> str"]}
        check_api_boundary(
            "signatures/transform.py",
            rule="nonfinite_unknown_field",
            contract_path=README,
            requirement_quote="未知额外字段可忽略，但其中非有限JSON仍非法",
            args=[[payload], contract],
        )
        check_api_boundary(
            "signatures/transform.py",
            rule="invalid_payload_type",
            contract_path=README,
            requirement_quote="仅对象/数组顶层合法；非法JSON、其他顶层类型和任意嵌套NaN/Infinity抛ValueError",
            args=[[payload], contract],
        )

    def test_parameters_boundary(self):
        contract = {"name": "parameters", "operation": "parameter_docs", "inputs": ["in.json"], "output": "out.json"}
        payload = {"objects": [{"id": "A", "doc": ":param x: hi", "namespace": "n", "aliases": {}, "mro": []}]}
        check_api_boundary(
            "parameters/transform.py",
            rule="nonfinite_unknown_field",
            contract_path=README,
            requirement_quote="未知额外字段可忽略，但其中非有限JSON仍非法",
            args=[[payload], contract],
        )
        check_api_boundary(
            "parameters/transform.py",
            rule="invalid_payload_type",
            contract_path=README,
            requirement_quote="仅对象/数组顶层合法；非法JSON、其他顶层类型和任意嵌套NaN/Infinity抛ValueError",
            args=[[payload], contract],
        )

    def test_inheritance_boundary(self):
        contract = {"name": "inheritance", "operation": "inherited_doc", "inputs": ["in.json"], "output": "out.json"}
        payload = {"objects": [{"id": "A", "doc": ":param x: hi", "namespace": "n", "aliases": {}, "mro": []}], "target": "A"}
        check_api_boundary(
            "inheritance/transform.py",
            rule="nonfinite_unknown_field",
            contract_path=README,
            requirement_quote="未知额外字段可忽略，但其中非有限JSON仍非法",
            args=[[payload], contract],
        )
        check_api_boundary(
            "inheritance/transform.py",
            rule="invalid_payload_type",
            contract_path=README,
            requirement_quote="仅对象/数组顶层合法；非法JSON、其他顶层类型和任意嵌套NaN/Infinity抛ValueError",
            args=[[payload], contract],
        )

    def test_document_boundary(self):
        contract = {"name": "document", "operation": "api_documentation", "inputs": ["a", "b", "c"], "output": "out.json"}
        sig = {"overloads": []}
        param = {"docs": {}}
        inherit = {"provider": None, "namespace": None, "aliases": {}}
        check_api_boundary(
            "document/transform.py",
            rule="nonfinite_unknown_field",
            contract_path=README,
            requirement_quote="未知额外字段可忽略，但其中非有限JSON仍非法",
            args=[[sig, param, inherit], contract],
        )
        check_api_boundary(
            "document/transform.py",
            rule="invalid_payload_type",
            contract_path=README,
            requirement_quote="仅对象/数组顶层合法；非法JSON、其他顶层类型和任意嵌套NaN/Infinity抛ValueError",
            args=[[sig, param, inherit], contract],
        )


class TestSignatures(unittest.TestCase):
    def test_overload_signatures_output(self):
        payload = {
            "overloads": [
                "f(x: int, /, *, strict: bool = False) -> str",
                "f(x: list[str], y = None) -> dict[str, int]",
            ]
        }
        contract = {"name": "signatures", "operation": "overload_signatures", "inputs": ["in.json"], "output": "out.json"}
        result = call_candidate("signatures/transform.py", "transform", args=[[payload], contract])
        self.assertEqual(result["name"], "signatures")
        overloads = result["result"]["overloads"]
        self.assertEqual(len(overloads), 2)
        first = overloads[0]
        self.assertEqual(first["name"], "f")
        self.assertEqual(first["returns"], "str")
        kinds = [p["kind"] for p in first["parameters"]]
        self.assertEqual(kinds, ["posonly", "kwonly"])
        self.assertEqual(first["parameters"][0]["annotation"], "int")
        self.assertEqual(first["parameters"][1]["default"], "False")
        second = overloads[1]
        self.assertEqual(second["parameters"][1]["default"], "None")
        self.assertIsNone(second["parameters"][1]["annotation"])


class TestParameters(unittest.TestCase):
    def test_parameter_docs_output(self):
        payload = {
            "objects": [
                {
                    "id": "Base",
                    "doc": ":param dict(str, str) x: mapping 47\n:param y: optional\n:type y: Item",
                    "namespace": "base",
                    "aliases": {"Item": "base.Item"},
                    "mro": [],
                }
            ]
        }
        contract = {"name": "parameters", "operation": "parameter_docs", "inputs": ["in.json"], "output": "out.json"}
        result = call_candidate("parameters/transform.py", "transform", args=[[payload], contract])
        docs = result["result"]["docs"]["Base"]
        self.assertEqual([d["name"] for d in docs], ["x", "y"])
        self.assertEqual(docs[0]["type"], "dict(str, str)")
        self.assertEqual(docs[0]["description"], "mapping 47")
        self.assertEqual(docs[1]["type"], "Item")
        self.assertEqual(docs[1]["description"], "optional")


class TestInheritance(unittest.TestCase):
    def test_inherited_doc_output(self):
        payload = {
            "objects": [
                {"id": "Base", "doc": ":param x: hi", "namespace": "base", "aliases": {"Item": "base.Item"}, "mro": []},
                {"id": "Child", "doc": "", "namespace": "child", "aliases": {"Item": "child.Item"}, "mro": ["Base"]},
            ],
            "target": "Child",
        }
        contract = {"name": "inheritance", "operation": "inherited_doc", "inputs": ["in.json"], "output": "out.json"}
        result = call_candidate("inheritance/transform.py", "transform", args=[[payload], contract])
        r = result["result"]
        self.assertEqual(r["provider"], "Base")
        self.assertEqual(r["namespace"], "base")
        self.assertEqual(r["aliases"], {"Item": "base.Item"})

    def test_inheritance_no_doc(self):
        payload = {
            "objects": [
                {"id": "Base", "doc": "", "namespace": "base", "aliases": {}, "mro": []},
                {"id": "Child", "doc": "", "namespace": "child", "aliases": {}, "mro": ["Base"]},
            ],
            "target": "Child",
        }
        contract = {"name": "inheritance", "operation": "inherited_doc", "inputs": ["in.json"], "output": "out.json"}
        result = call_candidate("inheritance/transform.py", "transform", args=[[payload], contract])
        r = result["result"]
        self.assertIsNone(r["provider"])
        self.assertIsNone(r["namespace"])
        self.assertEqual(r["aliases"], {})


class TestDocument(unittest.TestCase):
    def test_document_output(self):
        sig = {"overloads": [{"name": "f", "parameters": [], "returns": "str"}]}
        param = {"docs": {"Base": [{"name": "y", "type": "Item", "description": "optional"}]}}
        inherit = {"provider": "Base", "namespace": "base", "aliases": {"Item": "base.Item"}}
        contract = {"name": "document", "operation": "api_documentation", "inputs": ["a", "b", "c"], "output": "out.json"}
        result = call_candidate("document/transform.py", "transform", args=[[sig, param, inherit], contract])
        r = result["result"]
        self.assertEqual(r["provider"], "Base")
        self.assertEqual(r["namespace"], "base")
        self.assertEqual(r["parameters"][0]["type"], "base.Item")
        self.assertEqual(r["parameters"][0]["description"], "optional")

    def test_document_no_provider(self):
        sig = {"overloads": []}
        param = {"docs": {}}
        inherit = {"provider": None, "namespace": None, "aliases": {}}
        contract = {"name": "document", "operation": "api_documentation", "inputs": ["a", "b", "c"], "output": "out.json"}
        result = call_candidate("document/transform.py", "transform", args=[[sig, param, inherit], contract])
        self.assertEqual(result["result"]["parameters"], [])


if __name__ == "__main__":
    unittest.main()
