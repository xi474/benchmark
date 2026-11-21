import unittest

from visible_contract_check_sdk import call_candidate, CandidateCallError, check_api_boundary

README = "README.md"

API_BOUNDARY_REQUIREMENTS = [
    {
        "target_path": "engines/ordinary/transform.py",
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
        "target_path": "engines/annotations/transform.py",
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
        "target_path": "engines/comments/transform.py",
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
        "target_path": "engines/analysis/transform.py",
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


class TestOrdinaryUses(unittest.TestCase):
    def test_ordinary_excludes_annotations_and_comments(self):
        source = (
            "import os\n"
            "x: int = 1\n"
            "y = os.path.join('a', 'b')  # type: os.PathLike\n"
        )
        payload = {"source": source}
        contract = {"name": "ordinary", "operation": "ordinary_uses", "inputs": ["inputs/case.json"], "output": "outputs/ordinary.json"}
        result = call_candidate("engines/ordinary/transform.py", "transform", args=[[payload], contract])
        names = [(u["scope"], u["name"]) for u in result["result"]["uses"]]
        self.assertIn(("module", "os"), names)
        self.assertNotIn(("module", "int"), names)
        self.assertNotIn(("module", "PathLike"), names)

    def test_ordinary_function_scope(self):
        source = "def f(a):\n    return a + b\n"
        payload = {"source": source}
        contract = {"name": "ordinary", "operation": "ordinary_uses", "inputs": ["inputs/case.json"], "output": "outputs/ordinary.json"}
        result = call_candidate("engines/ordinary/transform.py", "transform", args=[[payload], contract])
        names = [(u["scope"], u["name"]) for u in result["result"]["uses"]]
        self.assertIn(("f", "a"), names)
        self.assertIn(("f", "b"), names)


class TestAnnotationUses(unittest.TestCase):
    def test_annotation_forward_string_reparse(self):
        source = "x: 'List[int]' = []\n"
        payload = {"source": source}
        contract = {"name": "annotations", "operation": "annotation_uses", "inputs": ["inputs/case.json"], "output": "outputs/annotations.json"}
        result = call_candidate("engines/annotations/transform.py", "transform", args=[[payload], contract])
        names = [(u["scope"], u["name"]) for u in result["result"]["uses"]]
        self.assertIn(("module", "List"), names)
        self.assertIn(("module", "int"), names)

    def test_annotation_bad_forward_raises(self):
        source = "x: 'List[' = []\n"
        payload = {"source": source}
        contract = {"name": "annotations", "operation": "annotation_uses", "inputs": ["inputs/case.json"], "output": "outputs/annotations.json"}
        with self.assertRaises(CandidateCallError) as cm:
            call_candidate("engines/annotations/transform.py", "transform", args=[[payload], contract])
        self.assertEqual(cm.exception.details["failure_phase"], "candidate_exception")
        self.assertEqual(cm.exception.details["error_type"], "ValueError")


class TestTypeCommentUses(unittest.TestCase):
    def test_type_comment_assign(self):
        source = "import abc\nX = None  # type: abc.ABC\n"
        payload = {"source": source}
        contract = {"name": "comments", "operation": "type_comment_uses", "inputs": ["inputs/case.json"], "output": "outputs/comments.json"}
        result = call_candidate("engines/comments/transform.py", "transform", args=[[payload], contract])
        names = [(u["scope"], u["name"]) for u in result["result"]["uses"]]
        self.assertIn(("module", "abc"), names)

    def test_type_comment_ignore_no_use(self):
        source = "import os\nX = None  # type: ignore\n"
        payload = {"source": source}
        contract = {"name": "comments", "operation": "type_comment_uses", "inputs": ["inputs/case.json"], "output": "outputs/comments.json"}
        result = call_candidate("engines/comments/transform.py", "transform", args=[[payload], contract])
        self.assertEqual(result["result"]["uses"], [])


class TestAnalysisJoin(unittest.TestCase):
    def test_analysis_unused_and_used_by(self):
        source = "import os\nimport json as j\nx = j.dumps({})\n"
        ordinary = {"uses": [{"scope": "module", "name": "j", "line": 3}]}
        annotations = {"uses": []}
        comments = {"uses": []}
        payloads = [{"source": source}, ordinary, annotations, comments]
        contract = {"name": "analysis", "operation": "import_usage_join", "inputs": ["inputs/case.json", "outputs/ordinary.json", "outputs/annotations.json", "outputs/comments.json"], "output": "outputs/analysis.json"}
        result = call_candidate("engines/analysis/transform.py", "transform", args=[payloads, contract])
        imports = result["result"]["imports"]
        by_name = {i["name"]: i for i in imports}
        self.assertEqual(by_name["j"]["used_by"], ["ordinary"])
        self.assertEqual(by_name["os"]["used_by"], [])
        self.assertEqual(result["result"]["unused"], ["module:os"])


class TestApiBoundaries(unittest.TestCase):
    def test_api_boundary_rules(self):
        for req in API_BOUNDARY_REQUIREMENTS:
            for rule_name, rule in req["rules"].items():
                if not rule.get("applicable", False):
                    continue
                with self.subTest(target=req["target_path"], rule=rule_name):
                    args = [{"source": "x = 1"}, {"name": "t", "operation": "op", "inputs": ["i"], "output": "o"}]
                    check_api_boundary(
                        req["target_path"],
                        rule=rule_name,
                        contract_path=rule["contract_path"],
                        requirement_quote=rule["requirement_quote"],
                        args=args,
                    )


if __name__ == "__main__":
    unittest.main()
