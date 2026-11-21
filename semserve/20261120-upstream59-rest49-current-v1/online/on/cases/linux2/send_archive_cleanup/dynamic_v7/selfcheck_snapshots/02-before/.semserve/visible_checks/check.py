import unittest

API_BOUNDARY_REQUIREMENTS = [
    {
        "target_path": "products/receipts/transform.py",
        "function": "transform",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": True,
                "contract_path": "README.md",
                "requirement_quote": "未知额外字段可忽略，但其中非有限JSON仍非法。",
            },
            "invalid_payload_type": {
                "applicable": True,
                "contract_path": "README.md",
                "requirement_quote": "仅对象/数组顶层合法；非法JSON、其他顶层类型和任意嵌套NaN/Infinity抛ValueError。",
            },
        },
    },
    {
        "target_path": "products/cleanup/transform.py",
        "function": "transform",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": True,
                "contract_path": "README.md",
                "requirement_quote": "未知额外字段可忽略，但其中非有限JSON仍非法。",
            },
            "invalid_payload_type": {
                "applicable": True,
                "contract_path": "README.md",
                "requirement_quote": "仅对象/数组顶层合法；非法JSON、其他顶层类型和任意嵌套NaN/Infinity抛ValueError。",
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
                "requirement_quote": "未知额外字段可忽略，但其中非有限JSON仍非法。",
            },
            "invalid_payload_type": {
                "applicable": True,
                "contract_path": "README.md",
                "requirement_quote": "仅对象/数组顶层合法；非法JSON、其他顶层类型和任意嵌套NaN/Infinity抛ValueError。",
            },
        },
    },
]


class TestReceipts(unittest.TestCase):
    def test_receipts_output_shape(self):
        payload = {
            "files": [{"path": "a.txt", "hex": "616263"}],
            "attachments": ["a.txt"],
            "recipients": ["ann"],
            "send_ok": {"ann": True},
        }
        contract = {"name": "receipts", "inputs": ["x"], "output": "y"}
        result = call_candidate(
            "products/receipts/transform.py", "transform",
            args=[[payload], contract],
        )
        self.assertEqual(set(result), {"name", "result"})
        self.assertEqual(result["name"], "receipts")
        r = result["result"]
        self.assertEqual(set(r), {"attachments", "receipts"})
        self.assertEqual(r["attachments"], [{"path": "a.txt", "sha256": "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"}])
        self.assertEqual(r["receipts"], [{"recipient": "ann", "ok": True}])

    def test_receipts_ok_false(self):
        payload = {
            "files": [{"path": "a.txt", "hex": "616263"}],
            "attachments": ["a.txt"],
            "recipients": ["ann"],
            "send_ok": {"ann": False},
        }
        contract = {"name": "receipts", "inputs": ["x"], "output": "y"}
        result = call_candidate(
            "products/receipts/transform.py", "transform",
            args=[[payload], contract],
        )
        self.assertEqual(result["result"]["receipts"], [{"recipient": "ann", "ok": False}])


class TestCleanup(unittest.TestCase):
    def test_cleanup_boundary(self):
        payload = {
            "files": [
                {"path": "home/tmp/a.tmp", "hex": "00"},
                {"path": "home/tmp-old/b.tmp", "hex": "00"},
                {"path": "home/tmp/c.txt", "hex": "00"},
            ],
            "cleanup_prefix": "home/tmp",
        }
        contract = {"name": "cleanup", "inputs": ["x"], "output": "y"}
        result = call_candidate(
            "products/cleanup/transform.py", "transform",
            args=[[payload], contract],
        )
        self.assertEqual(result["result"]["delete"], ["home/tmp/a.tmp"])


class TestArchive(unittest.TestCase):
    def test_archive_blocked_when_not_all_ok(self):
        snapshot = {
            "archive_prefix": "archive",
            "attachments": ["a.txt"],
            "files": [{"path": "a.txt", "hex": "616263"}],
        }
        receipts = {"receipts": [{"recipient": "ann", "ok": False}]}
        cleanup = {"delete": []}
        contract = {"name": "archive", "inputs": ["a", "b", "c"], "output": "y"}
        result = call_candidate(
            "products/archive/transform.py", "transform",
            args=[[snapshot, receipts, cleanup], contract],
        )
        r = result["result"]
        self.assertEqual(r["moves"], [])
        self.assertTrue(r["blocked"])

    def test_archive_moves_when_all_ok(self):
        snapshot = {
            "archive_prefix": "archive",
            "attachments": ["a.txt"],
            "files": [{"path": "a.txt", "hex": "616263"}],
        }
        receipts = {"receipts": [{"recipient": "ann", "ok": True}]}
        cleanup = {"delete": []}
        contract = {"name": "archive", "inputs": ["a", "b", "c"], "output": "y"}
        result = call_candidate(
            "products/archive/transform.py", "transform",
            args=[[snapshot, receipts, cleanup], contract],
        )
        r = result["result"]
        self.assertEqual(r["moves"], [{"from": "a.txt", "to": "archive/a.txt"}])
        self.assertFalse(r["blocked"])


class TestApiBoundary(unittest.TestCase):
    def test_receipts_boundary(self):
        payload = {
            "files": [{"path": "a.txt", "hex": "616263"}],
            "attachments": ["a.txt"],
            "recipients": ["ann"],
            "send_ok": {"ann": True},
        }
        contract = {"name": "receipts", "inputs": ["x"], "output": "y"}
        check_api_boundary(
            "products/receipts/transform.py", rule="nonfinite_unknown_field",
            contract_path="README.md",
            requirement_quote="未知额外字段可忽略，但其中非有限JSON仍非法。",
            args=[[payload], contract],
        )
        check_api_boundary(
            "products/receipts/transform.py", rule="invalid_payload_type",
            contract_path="README.md",
            requirement_quote="仅对象/数组顶层合法；非法JSON、其他顶层类型和任意嵌套NaN/Infinity抛ValueError。",
            args=[[payload], contract],
        )

    def test_cleanup_boundary(self):
        payload = {
            "files": [{"path": "home/tmp/a.tmp", "hex": "00"}],
            "cleanup_prefix": "home/tmp",
        }
        contract = {"name": "cleanup", "inputs": ["x"], "output": "y"}
        check_api_boundary(
            "products/cleanup/transform.py", rule="nonfinite_unknown_field",
            contract_path="README.md",
            requirement_quote="未知额外字段可忽略，但其中非有限JSON仍非法。",
            args=[[payload], contract],
        )
        check_api_boundary(
            "products/cleanup/transform.py", rule="invalid_payload_type",
            contract_path="README.md",
            requirement_quote="仅对象/数组顶层合法；非法JSON、其他顶层类型和任意嵌套NaN/Infinity抛ValueError。",
            args=[[payload], contract],
        )

    def test_archive_boundary(self):
        snapshot = {
            "archive_prefix": "archive",
            "attachments": ["a.txt"],
            "files": [{"path": "a.txt", "hex": "616263"}],
        }
        receipts = {"receipts": [{"recipient": "ann", "ok": True}]}
        cleanup = {"delete": []}
        contract = {"name": "archive", "inputs": ["a", "b", "c"], "output": "y"}
        check_api_boundary(
            "products/archive/transform.py", rule="nonfinite_unknown_field",
            contract_path="README.md",
            requirement_quote="未知额外字段可忽略，但其中非有限JSON仍非法。",
            args=[[snapshot, receipts, cleanup], contract],
        )
        check_api_boundary(
            "products/archive/transform.py", rule="invalid_payload_type",
            contract_path="README.md",
            requirement_quote="仅对象/数组顶层合法；非法JSON、其他顶层类型和任意嵌套NaN/Infinity抛ValueError。",
            args=[[snapshot, receipts, cleanup], contract],
        )


if __name__ == "__main__":
    unittest.main()
