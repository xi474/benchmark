import unittest

API_BOUNDARY_REQUIREMENTS = [
    {
        "target_path": "products/chunks/transform.py",
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
        "target_path": "products/layout/transform.py",
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
        "target_path": "products/restore/transform.py",
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


class TestChunksTransform(unittest.TestCase):
    def test_chunks_output_contract(self):
        payload = {
            "files": [{"path": "a.txt", "hex": "616263"}],
            "max_file_bytes": 16,
            "max_entries": 2,
        }
        contract = {"name": "chunks", "operation": "reshard_chunks", "inputs": ["x"], "output": "y"}
        result = call_candidate("products/chunks/transform.py", "transform", args=[[payload], contract])
        self.assertEqual(set(result), {"name", "result"})
        self.assertEqual(result["name"], "chunks")
        r = result["result"]
        self.assertEqual(set(r), {"chunks", "manifest"})
        self.assertEqual(r["chunks"], [{"name": "d000000.bin", "hex": "616263"}])
        self.assertEqual(r["manifest"]["files"][0]["parts"], ["d000000.bin"])
        self.assertEqual(r["manifest"]["files"][0]["size"], 3)
        self.assertEqual(r["manifest"]["files"][0]["sha256"],
                         "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad")

    def test_chunks_empty_file_no_chunk(self):
        payload = {
            "files": [{"path": "a.txt", "hex": ""}],
            "max_file_bytes": 16,
            "max_entries": 2,
        }
        contract = {"name": "chunks", "operation": "reshard_chunks", "inputs": ["x"], "output": "y"}
        result = call_candidate("products/chunks/transform.py", "transform", args=[[payload], contract])
        r = result["result"]
        self.assertEqual(r["chunks"], [])
        self.assertEqual(r["manifest"]["files"][0]["parts"], [])
        self.assertEqual(r["manifest"]["files"][0]["size"], 0)

    def test_chunks_split_across_blocks(self):
        payload = {
            "files": [{"path": "a.txt", "hex": "6162636465"}],
            "max_file_bytes": 16,
            "max_entries": 2,
        }
        contract = {"name": "chunks", "operation": "reshard_chunks", "inputs": ["x"], "output": "y"}
        result = call_candidate("products/chunks/transform.py", "transform", args=[[payload], contract])
        r = result["result"]
        self.assertEqual([c["name"] for c in r["chunks"]], ["d000000.bin"])
        self.assertEqual([c["hex"] for c in r["chunks"]], ["6162636465"])
        self.assertEqual(r["manifest"]["files"][0]["parts"], ["d000000.bin"])

    def test_chunks_bool_max_file_bytes_rejected(self):
        payload = {
            "files": [{"path": "a.txt", "hex": "61"}],
            "max_file_bytes": True,
            "max_entries": 2,
        }
        contract = {"name": "chunks", "operation": "reshard_chunks", "inputs": ["x"], "output": "y"}
        with self.assertRaises(CandidateCallError) as cm:
            call_candidate("products/chunks/transform.py", "transform", args=[[payload], contract])
        self.assertEqual(cm.exception.details["failure_phase"], "candidate_exception")
        self.assertEqual(cm.exception.details["error_type"], "ValueError")


class TestLayoutTransform(unittest.TestCase):
    def test_layout_output_contract(self):
        original = {"max_file_bytes": 16, "max_entries": 2}
        chunks = {"name": "chunks", "result": {
            "chunks": [{"name": "d000000.bin", "hex": "616263"}],
            "manifest": {"files": [{"path": "a.txt", "size": 3,
                                     "sha256": "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
                                     "parts": ["d000000.bin"]}]},
        }}
        contract = {"name": "layout", "operation": "reshard_layout", "inputs": ["x", "y"], "output": "z"}
        result = call_candidate("products/layout/transform.py", "transform",
                                args=[[original, chunks], contract])
        r = result["result"]
        self.assertEqual(set(r), {"tree", "max_entries", "max_file_bytes"})
        self.assertEqual(r["max_entries"], 2)
        self.assertEqual(r["max_file_bytes"], 16)
        names = [e["path"].split("/")[-1] for e in r["tree"]]
        self.assertEqual(len(names), len(set(names)))
        self.assertIn("d000000.bin", names)
        self.assertTrue(any(n.startswith("m") for n in names))


class TestRestoreTransform(unittest.TestCase):
    def test_restore_roundtrip(self):
        import json
        manifest = {"files": [{"path": "a.txt", "size": 3,
                               "sha256": "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
                               "parts": ["d000000.bin"]}]}
        mb = json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        tree = [{"path": "d000000.bin", "hex": "616263"}]
        for i in range(0, len(mb), 16):
            tree.append({"path": "m%06d.bin" % (i // 16), "hex": mb[i:i+16].hex()})
        layout = {"name": "layout", "result": {"tree": tree, "max_entries": 4, "max_file_bytes": 64}}
        contract = {"name": "restore", "operation": "reshard_restore", "inputs": ["x"], "output": "y"}
        result = call_candidate("products/restore/transform.py", "transform", args=[[layout], contract])
        r = result["result"]
        self.assertEqual(set(r), {"files", "total_bytes"})
        self.assertEqual(r["files"], [{"path": "a.txt", "hex": "616263"}])
        self.assertEqual(r["total_bytes"], 3)

    def test_restore_sha_mismatch_rejected(self):
        import json
        manifest = {"files": [{"path": "a.txt", "size": 3,
                               "sha256": "00" * 32,
                               "parts": ["d000000.bin"]}]}
        mb = json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        tree = [{"path": "d000000.bin", "hex": "616263"}]
        for i in range(0, len(mb), 16):
            tree.append({"path": "m%06d.bin" % (i // 16), "hex": mb[i:i+16].hex()})
        layout = {"name": "layout", "result": {"tree": tree, "max_entries": 4, "max_file_bytes": 64}}
        contract = {"name": "restore", "operation": "reshard_restore", "inputs": ["x"], "output": "y"}
        with self.assertRaises(CandidateCallError) as cm:
            call_candidate("products/restore/transform.py", "transform", args=[[layout], contract])
        self.assertEqual(cm.exception.details["failure_phase"], "candidate_exception")
        self.assertEqual(cm.exception.details["error_type"], "ValueError")


class TestApiBoundary(unittest.TestCase):
    def test_chunks_boundary(self):
        payload = {"files": [{"path": "a.txt", "hex": "616263"}], "max_file_bytes": 16, "max_entries": 2}
        contract = {"name": "chunks", "operation": "reshard_chunks", "inputs": ["x"], "output": "y"}
        check_api_boundary("products/chunks/transform.py", rule="nonfinite_unknown_field",
            contract_path="README.md", requirement_quote="未知额外字段可忽略，但其中非有限JSON仍非法",
            args=[[payload], contract])
        check_api_boundary("products/chunks/transform.py", rule="invalid_payload_type",
            contract_path="README.md", requirement_quote="仅对象/数组顶层合法；非法JSON、其他顶层类型和任意嵌套NaN/Infinity抛ValueError",
            args=[[payload], contract])

    def test_layout_boundary(self):
        original = {"max_file_bytes": 16, "max_entries": 2}
        chunks = {"name": "chunks", "result": {"chunks": [{"name": "d000000.bin", "hex": "616263"}],
            "manifest": {"files": [{"path": "a.txt", "size": 3, "sha256": "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad", "parts": ["d000000.bin"]}]}}}
        contract = {"name": "layout", "operation": "reshard_layout", "inputs": ["x", "y"], "output": "z"}
        check_api_boundary("products/layout/transform.py", rule="nonfinite_unknown_field",
            contract_path="README.md", requirement_quote="未知额外字段可忽略，但其中非有限JSON仍非法",
            args=[[original, chunks], contract])
        check_api_boundary("products/layout/transform.py", rule="invalid_payload_type",
            contract_path="README.md", requirement_quote="仅对象/数组顶层合法；非法JSON、其他顶层类型和任意嵌套NaN/Infinity抛ValueError",
            args=[[original, chunks], contract])

    def test_restore_boundary(self):
        import json
        manifest = {"files": [{"path": "a.txt", "size": 3, "sha256": "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad", "parts": ["d000000.bin"]}]}
        mb = json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        tree = [{"path": "d000000.bin", "hex": "616263"}]
        for i in range(0, len(mb), 16):
            tree.append({"path": "m%06d.bin" % (i // 16), "hex": mb[i:i+16].hex()})
        layout = {"name": "layout", "result": {"tree": tree, "max_entries": 4, "max_file_bytes": 64}}
        contract = {"name": "restore", "operation": "reshard_restore", "inputs": ["x"], "output": "y"}
        check_api_boundary("products/restore/transform.py", rule="nonfinite_unknown_field",
            contract_path="README.md", requirement_quote="未知额外字段可忽略，但其中非有限JSON仍非法",
            args=[[layout], contract])
        check_api_boundary("products/restore/transform.py", rule="invalid_payload_type",
            contract_path="README.md", requirement_quote="仅对象/数组顶层合法；非法JSON、其他顶层类型和任意嵌套NaN/Infinity抛ValueError",
            args=[[layout], contract])


if __name__ == "__main__":
    unittest.main()
