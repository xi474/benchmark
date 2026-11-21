import unittest

API_BOUNDARY_REQUIREMENTS = [
    {
        "target_path": "products/inventory/transform.py",
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
        "target_path": "products/selection/transform.py",
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
        "target_path": "products/archive/transform.py",
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


class TestApiBoundary(unittest.TestCase):
    def test_inventory_boundary(self):
        payload = {
            "files": [{"path": "a.txt", "kind": "file", "hex": "6162", "target": None}],
            "manifest": None,
            "build_ignore": None,
        }
        contract = {"name": "inventory", "inputs": ["x"], "output": "y"}
        check_api_boundary(
            "products/inventory/transform.py",
            rule="nonfinite_unknown_field",
            contract_path="README.md",
            requirement_quote="未知额外字段可忽略，但其中非有限JSON仍非法",
            args=[[payload], contract],
        )
        check_api_boundary(
            "products/inventory/transform.py",
            rule="invalid_payload_type",
            contract_path="README.md",
            requirement_quote="仅对象/数组顶层合法；非法JSON、其他顶层类型和任意嵌套NaN/Infinity抛ValueError",
            args=[[payload], contract],
        )

    def test_selection_boundary(self):
        snapshot = {
            "files": [],
            "manifest": None,
            "build_ignore": None,
        }
        inventory = {"files": [{"path": "a.py", "hex": "00"}], "symlinks": []}
        contract = {"name": "selection", "inputs": ["a", "b"], "output": "y"}
        check_api_boundary(
            "products/selection/transform.py",
            rule="nonfinite_unknown_field",
            contract_path="README.md",
            requirement_quote="未知额外字段可忽略，但其中非有限JSON仍非法",
            args=[[snapshot, inventory], contract],
        )
        check_api_boundary(
            "products/selection/transform.py",
            rule="invalid_payload_type",
            contract_path="README.md",
            requirement_quote="仅对象/数组顶层合法；非法JSON、其他顶层类型和任意嵌套NaN/Infinity抛ValueError",
            args=[[snapshot, inventory], contract],
        )

    def test_archive_boundary(self):
        inventory = {"files": [{"path": "a.txt", "hex": "616263"}], "symlinks": []}
        selection = {"selected": ["a.txt"]}
        contract = {"name": "archive", "inputs": ["a", "b"], "output": "y"}
        check_api_boundary(
            "products/archive/transform.py",
            rule="nonfinite_unknown_field",
            contract_path="README.md",
            requirement_quote="未知额外字段可忽略，但其中非有限JSON仍非法",
            args=[[inventory, selection], contract],
        )
        check_api_boundary(
            "products/archive/transform.py",
            rule="invalid_payload_type",
            contract_path="README.md",
            requirement_quote="仅对象/数组顶层合法；非法JSON、其他顶层类型和任意嵌套NaN/Infinity抛ValueError",
            args=[[inventory, selection], contract],
        )


class TestInventory(unittest.TestCase):
    def test_inventory_output_shape(self):
        payload = {
            "files": [
                {"path": "a.txt", "kind": "file", "hex": "6162", "target": None},
                {"path": "link", "kind": "symlink", "hex": "", "target": "a.txt"},
            ],
            "manifest": None,
            "build_ignore": None,
        }
        contract = {"name": "inventory", "inputs": ["x"], "output": "y"}
        result = call_candidate(
            "products/inventory/transform.py", "transform", args=[[payload], contract]
        )
        self.assertEqual(result["name"], "inventory")
        self.assertEqual(
            result["result"],
            {"files": [{"path": "a.txt", "hex": "6162"}], "symlinks": ["link"]},
        )

    def test_inventory_rejects_unsafe_path(self):
        payload = {
            "files": [{"path": "../a.txt", "kind": "file", "hex": "6162", "target": None}],
            "manifest": None,
            "build_ignore": None,
        }
        contract = {"name": "inventory", "inputs": ["x"], "output": "y"}
        with self.assertRaises(CandidateCallError) as cm:
            call_candidate(
                "products/inventory/transform.py", "transform", args=[[payload], contract]
            )
        self.assertEqual(cm.exception.details["failure_phase"], "candidate_exception")
        self.assertEqual(cm.exception.details["error_type"], "ValueError")


class TestSelection(unittest.TestCase):
    def test_selection_manifest_instructions(self):
        snapshot = {
            "files": [],
            "manifest": "include README.md\nrecursive-include plugins *.py\nexclude plugins/tests/*\ninclude .git/config\n",
            "build_ignore": None,
        }
        inventory = {
            "files": [
                {"path": "README.md", "hex": "00"},
                {"path": "plugins/a.py", "hex": "00"},
                {"path": "plugins/tests/t.py", "hex": "00"},
                {"path": ".git/config", "hex": "00"},
                {"path": "plugins/a.pyc", "hex": "00"},
                {"path": "MANIFEST.in", "hex": "00"},
            ],
            "symlinks": [],
        }
        contract = {"name": "selection", "inputs": ["a", "b"], "output": "y"}
        result = call_candidate(
            "products/selection/transform.py",
            "transform",
            args=[[snapshot, inventory], contract],
        )
        self.assertEqual(result["result"]["selected"], ["README.md", "plugins/a.py"])

    def test_selection_build_ignore(self):
        snapshot = {
            "files": [],
            "manifest": None,
            "build_ignore": ["*.pyc", "docs/*"],
        }
        inventory = {
            "files": [
                {"path": "a.py", "hex": "00"},
                {"path": "a.pyc", "hex": "00"},
                {"path": "docs/x.txt", "hex": "00"},
            ],
            "symlinks": [],
        }
        contract = {"name": "selection", "inputs": ["a", "b"], "output": "y"}
        result = call_candidate(
            "products/selection/transform.py",
            "transform",
            args=[[snapshot, inventory], contract],
        )
        self.assertEqual(result["result"]["selected"], ["a.py"])

    def test_selection_manifest_and_ignore_conflict(self):
        snapshot = {
            "files": [],
            "manifest": "include a.py\n",
            "build_ignore": ["*.pyc"],
        }
        inventory = {"files": [{"path": "a.py", "hex": "00"}], "symlinks": []}
        contract = {"name": "selection", "inputs": ["a", "b"], "output": "y"}
        with self.assertRaises(CandidateCallError) as cm:
            call_candidate(
                "products/selection/transform.py",
                "transform",
                args=[[snapshot, inventory], contract],
            )
        self.assertEqual(cm.exception.details["failure_phase"], "candidate_exception")
        self.assertEqual(cm.exception.details["error_type"], "ValueError")


class TestArchive(unittest.TestCase):
    def test_archive_sha256_over_bytes(self):
        inventory = {"files": [{"path": "a.txt", "hex": "616263"}], "symlinks": []}
        selection = {"selected": ["a.txt"]}
        contract = {"name": "archive", "inputs": ["a", "b"], "output": "y"}
        result = call_candidate(
            "products/archive/transform.py",
            "transform",
            args=[[inventory, selection], contract],
        )
        import hashlib

        expected_sha = hashlib.sha256(b"abc").hexdigest()
        self.assertEqual(
            result["result"],
            {
                "entries": [{"path": "a.txt", "size": 3, "sha256": expected_sha}],
                "total_bytes": 3,
            },
        )

    def test_archive_rejects_unknown_selected(self):
        inventory = {"files": [{"path": "a.txt", "hex": "616263"}], "symlinks": []}
        selection = {"selected": ["missing.txt"]}
        contract = {"name": "archive", "inputs": ["a", "b"], "output": "y"}
        with self.assertRaises(CandidateCallError) as cm:
            call_candidate(
                "products/archive/transform.py",
                "transform",
                args=[[inventory, selection], contract],
            )
        self.assertEqual(cm.exception.details["failure_phase"], "candidate_exception")
        self.assertEqual(cm.exception.details["error_type"], "ValueError")


if __name__ == "__main__":
    unittest.main()
