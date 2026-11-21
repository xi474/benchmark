import unittest

API_BOUNDARY_REQUIREMENTS = [
    {
        "target_path": "parts/transform.py",
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
        "target_path": "encoding/transform.py",
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
        "target_path": "body/transform.py",
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


class TestPartsTransform(unittest.TestCase):
    def test_parts_output_shape_and_ordering(self):
        payload = {
            "boundary": "B1",
            "fields": {"b": "hello", "a": "world"},
            "files": {},
        }
        contract = {"name": "parts", "operation": "multipart_parts", "inputs": ["x"], "output": "y"}
        result = call_candidate("parts/transform.py", "transform", args=[[payload], contract])
        self.assertEqual(result["name"], "parts")
        parts = result["result"]["parts"]
        self.assertEqual([p["name"] for p in parts], ["a", "b"])
        self.assertEqual(parts[0]["hex"], "world".encode("utf-8").hex())
        self.assertEqual(parts[0]["mimetype"], "text/plain")
        self.assertEqual(parts[0]["encoding"], "raw")
        self.assertIsNone(parts[0]["filename"])

    def test_parts_file_base64(self):
        payload = {
            "boundary": "B1",
            "fields": {"f": {"filename": "data/x.bin"}},
            "files": {"data/x.bin": "00ff"},
        }
        contract = {"name": "parts", "operation": "multipart_parts", "inputs": ["x"], "output": "y"}
        result = call_candidate("parts/transform.py", "transform", args=[[payload], contract])
        part = result["result"]["parts"][0]
        self.assertEqual(part["name"], "f")
        self.assertEqual(part["filename"], "x.bin")
        self.assertEqual(part["encoding"], "base64")
        self.assertEqual(part["hex"], "00ff")
        self.assertEqual(part["mimetype"], "application/octet-stream")

    def test_parts_missing_file_raises(self):
        payload = {
            "boundary": "B1",
            "fields": {"f": {"filename": "data/missing.bin"}},
            "files": {},
        }
        contract = {"name": "parts", "operation": "multipart_parts", "inputs": ["x"], "output": "y"}
        with self.assertRaises(CandidateCallError) as cm:
            call_candidate("parts/transform.py", "transform", args=[[payload], contract])
        self.assertEqual(cm.exception.details["failure_phase"], "candidate_exception")
        self.assertEqual(cm.exception.details["error_type"], "ValueError")


class TestEncodingTransform(unittest.TestCase):
    def test_encoding_base64_wrap(self):
        import base64
        payload = {
            "parts": [
                {"name": "a", "filename": None, "mimetype": "application/octet-stream",
                 "encoding": "base64", "hex": "00ff10"}
            ]
        }
        contract = {"name": "encoding", "operation": "multipart_encoding", "inputs": ["x"], "output": "y"}
        result = call_candidate("encoding/transform.py", "transform", args=[[payload], contract])
        part = result["result"]["parts"][0]
        expected = base64.b64encode(bytes.fromhex("00ff10")).decode("ascii")
        self.assertEqual(bytes.fromhex(part["payload_hex"]).decode("ascii"), expected)
        self.assertEqual(part["encoding"], "base64")

    def test_encoding_raw_preserved(self):
        payload = {
            "parts": [
                {"name": "a", "filename": None, "mimetype": "text/plain",
                 "encoding": "raw", "hex": "c3a9"}
            ]
        }
        contract = {"name": "encoding", "operation": "multipart_encoding", "inputs": ["x"], "output": "y"}
        result = call_candidate("encoding/transform.py", "transform", args=[[payload], contract])
        part = result["result"]["parts"][0]
        self.assertEqual(part["payload_hex"], "c3a9")

    def test_encoding_unknown_encoding_raises(self):
        payload = {
            "parts": [
                {"name": "a", "filename": None, "mimetype": "text/plain",
                 "encoding": "bogus", "hex": "00"}
            ]
        }
        contract = {"name": "encoding", "operation": "multipart_encoding", "inputs": ["x"], "output": "y"}
        with self.assertRaises(CandidateCallError) as cm:
            call_candidate("encoding/transform.py", "transform", args=[[payload], contract])
        self.assertEqual(cm.exception.details["failure_phase"], "candidate_exception")
        self.assertEqual(cm.exception.details["error_type"], "ValueError")


class TestBodyTransform(unittest.TestCase):
    def test_body_content_type_and_boundary(self):
        snapshot = {"boundary": "B1"}
        encoding = {
            "parts": [
                {"name": "t", "filename": None, "mimetype": "text/plain",
                 "encoding": "raw", "payload_hex": "6869"}
            ]
        }
        contract = {"name": "body", "operation": "multipart_body", "inputs": ["a", "b"], "output": "y"}
        result = call_candidate("body/transform.py", "transform", args=[[snapshot, encoding], contract])
        self.assertEqual(result["result"]["content_type"], "multipart/form-data; boundary=B1")
        body = bytes.fromhex(result["result"]["body_hex"])
        self.assertTrue(body.startswith(b"--B1\r\n"))
        self.assertTrue(body.endswith(b"--B1--\r\n"))
        self.assertIn(b"Content-Disposition: form-data; name=\"t\"\r\n", body)
        self.assertIn(b"\r\n\r\nhi\r\n", body)

    def test_body_boundary_collision_raises(self):
        snapshot = {"boundary": "B1"}
        encoding = {
            "parts": [
                {"name": "t", "filename": None, "mimetype": "text/plain",
                 "encoding": "raw", "payload_hex": "4231"}
            ]
        }
        contract = {"name": "body", "operation": "multipart_body", "inputs": ["a", "b"], "output": "y"}
        with self.assertRaises(CandidateCallError) as cm:
            call_candidate("body/transform.py", "transform", args=[[snapshot, encoding], contract])
        self.assertEqual(cm.exception.details["failure_phase"], "candidate_exception")
        self.assertEqual(cm.exception.details["error_type"], "ValueError")


class TestApiBoundaries(unittest.TestCase):
    def test_api_boundary_rules(self):
        for req in API_BOUNDARY_REQUIREMENTS:
            for rule_name, rule in req["rules"].items():
                with self.subTest(target=req["target_path"], rule=rule_name):
                    if not rule.get("applicable", False):
                        continue
                    check_api_boundary(
                        req["target_path"],
                        rule=rule_name,
                        contract_path=rule["contract_path"],
                        requirement_quote=rule["requirement_quote"],
                        args=rule.get("args"),
                    )


if __name__ == "__main__":
    unittest.main()
