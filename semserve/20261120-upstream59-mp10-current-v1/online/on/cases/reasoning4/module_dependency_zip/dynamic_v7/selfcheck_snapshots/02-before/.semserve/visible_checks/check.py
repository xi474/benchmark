import unittest

README = "README.md"

API_BOUNDARY_REQUIREMENTS = [
    {
        "target_path": "engines/scanner/transform.py",
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
        "target_path": "engines/dependencies/transform.py",
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
        "target_path": "engines/payload/transform.py",
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


class ScannerBehavior(unittest.TestCase):
    def test_scanner_imports_and_module_paths(self):
        payload = {
            "modules": {
                "main.py": "import pkg.a\n",
                "pkg/__init__.py": "from . import b\n",
                "pkg/a.py": "from . import b\nimport six.moves.urllib.parse\n",
                "pkg/b.py": "from . import a\nimport json\n",
                "unused.py": "print('unused')\n",
            },
            "entry": "main.py",
            "externals": ["json", "urllib"],
            "aliases": {"six.moves.urllib.parse": "urllib.parse"},
        }
        contract = {"name": "scanner", "operation": "module_import_scan",
                    "inputs": ["inputs/case.json"], "output": "outputs/scanner.json"}
        result = call_candidate("engines/scanner/transform.py", "transform",
                                args=[[payload], contract])
        self.assertEqual(result["name"], "scanner")
        r = result["result"]
        self.assertEqual(r["imports"]["main.py"], ["pkg.a"])
        self.assertEqual(r["imports"]["pkg/__init__.py"], ["pkg.b"])
        self.assertEqual(r["imports"]["pkg/a.py"], ["pkg.b", "six.moves.urllib.parse"])
        self.assertEqual(r["imports"]["pkg/b.py"], ["json", "pkg.a"])
        self.assertEqual(r["imports"]["unused.py"], [])
        self.assertEqual(r["module_paths"]["main"], "main.py")
        self.assertEqual(r["module_paths"]["pkg"], "pkg/__init__.py")
        self.assertEqual(r["module_paths"]["pkg.a"], "pkg/a.py")
        self.assertEqual(r["module_paths"]["pkg.b"], "pkg/b.py")
        self.assertEqual(r["module_paths"]["unused"], "unused.py")


class DependenciesBehavior(unittest.TestCase):
    def test_dependency_closure(self):
        modules_payload = {
            "modules": {
                "main.py": "import pkg.a\n",
                "pkg/__init__.py": "from . import b\n",
                "pkg/a.py": "from . import b\nimport six.moves.urllib.parse\n",
                "pkg/b.py": "from . import a\nimport json\n",
                "unused.py": "print('unused')\n",
            },
            "entry": "main.py",
            "externals": ["json", "urllib"],
            "aliases": {"six.moves.urllib.parse": "urllib.parse"},
        }
        scan_payload = {
            "imports": {
                "main.py": ["pkg.a"],
                "pkg/__init__.py": ["pkg.b"],
                "pkg/a.py": ["pkg.b", "six.moves.urllib.parse"],
                "pkg/b.py": ["json", "pkg.a"],
                "unused.py": [],
            },
            "module_paths": {
                "main": "main.py",
                "pkg": "pkg/__init__.py",
                "pkg.a": "pkg/a.py",
                "pkg.b": "pkg/b.py",
                "unused": "unused.py",
            },
        }
        contract = {"name": "dependencies", "operation": "module_dependency_closure",
                    "inputs": ["inputs/case.json", "outputs/scanner.json"],
                    "output": "outputs/dependencies.json"}
        result = call_candidate("engines/dependencies/transform.py", "transform",
                                args=[[modules_payload, scan_payload], contract])
        r = result["result"]
        self.assertEqual(r["paths"], ["main.py", "pkg/__init__.py", "pkg/a.py", "pkg/b.py"])
        self.assertEqual(r["external"], ["json", "urllib.parse"])


class PayloadBehavior(unittest.TestCase):
    def test_payload_zip_deterministic(self):
        modules_payload = {
            "modules": {
                "main.py": "import pkg.a\n",
                "pkg/__init__.py": "from . import b\n",
                "pkg/a.py": "from . import b\nimport six.moves.urllib.parse\n",
                "pkg/b.py": "from . import a\nimport json\n",
            },
            "entry": "main.py",
            "externals": ["json", "urllib"],
            "aliases": {"six.moves.urllib.parse": "urllib.parse"},
        }
        closure_payload = {
            "paths": ["main.py", "pkg/__init__.py", "pkg/a.py", "pkg/b.py"],
            "external": ["json", "urllib.parse"],
        }
        contract = {"name": "payload", "operation": "module_zip",
                    "inputs": ["inputs/case.json", "outputs/dependencies.json"],
                    "output": "outputs/payload.json"}
        result = call_candidate("engines/payload/transform.py", "transform",
                                args=[[modules_payload, closure_payload], contract])
        r = result["result"]
        self.assertEqual(r["paths"], ["__init__.py", "main.py", "pkg/__init__.py",
                                      "pkg/a.py", "pkg/b.py"])
        self.assertEqual(r["external"], ["json", "urllib.parse"])
        self.assertEqual(len(r["sha256"]), 64)
        self.assertEqual(len(r["zip_hex"]) % 2, 0)


class ApiBoundary(unittest.TestCase):
    def test_api_boundaries(self):
        for req in API_BOUNDARY_REQUIREMENTS:
            for rule, spec in req["rules"].items():
                with self.subTest(target=req["target_path"], rule=rule):
                    if not spec.get("applicable", False):
                        continue
                    if req["target_path"].endswith("scanner/transform.py"):
                        args = [[{"modules": {"main.py": "import json\n"},
                                  "entry": "main.py", "externals": ["json"],
                                  "aliases": {}}],
                                {"name": "scanner", "inputs": ["a"], "output": "o"}]
                    elif req["target_path"].endswith("dependencies/transform.py"):
                        args = [[{"modules": {"main.py": "import json\n"},
                                  "entry": "main.py", "externals": ["json"],
                                  "aliases": {}},
                                 {"imports": {"main.py": ["json"]},
                                  "module_paths": {"main": "main.py"}}],
                                {"name": "dependencies", "inputs": ["a", "b"],
                                 "output": "o"}]
                    else:
                        args = [[{"modules": {"main.py": "import json\n"},
                                  "entry": "main.py", "externals": ["json"],
                                  "aliases": {}},
                                 {"paths": ["main.py"], "external": ["json"]}],
                                {"name": "payload", "inputs": ["a", "b"],
                                 "output": "o"}]
                    check_api_boundary(
                        req["target_path"], rule=rule,
                        contract_path=spec["contract_path"],
                        requirement_quote=spec["requirement_quote"],
                        args=args,
                    )


if __name__ == "__main__":
    unittest.main()
