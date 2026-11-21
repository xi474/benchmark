import unittest

API_BOUNDARY_REQUIREMENTS = [
    {
        "target_path": "solution.py",
        "function": "transform",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": False,
                "contract_path": "TASK.md",
                "requirement_quote": "输入elf_hex为合法ELF32 little-endian ET_EXEC、EM_MIPS程序",
                "reason": "The public contract does not state that transform rejects non-finite values in unknown fields.",
            },
            "invalid_payload_type": {
                "applicable": False,
                "contract_path": "TASK.md",
                "requirement_quote": "核心接口transform(payload)返回下述JSON结果",
                "reason": "The public contract does not state that transform raises ValueError for a non-object payload.",
            },
        },
    },
]


class TestTransformPublicContract(unittest.TestCase):
    def test_transform_returns_expected_public_result(self):
        import json
        from pathlib import Path

        payload = json.loads(Path("public_input.json").read_text(encoding="utf-8"))
        expected = json.loads(Path("public_expected.json").read_text(encoding="utf-8"))

        result = call_candidate("solution.py", "transform", args=[payload])

        self.assertIsInstance(result, dict)
        self.assertEqual(result["exit_code"], expected["exit_code"])
        self.assertEqual(result["registers"], expected["registers"])
        self.assertEqual(result["hi"], expected["hi"])
        self.assertEqual(result["lo"], expected["lo"])
        self.assertEqual(result["steps"], expected["steps"])
        self.assertEqual(result["stdout_hex"], expected["stdout_hex"])
        self.assertEqual(result["stderr_hex"], expected["stderr_hex"])
        self.assertEqual(result["files"], expected["files"])
        self.assertEqual(result["inspect"], expected["inspect"])
        self.assertEqual(result["syscalls"], expected["syscalls"])

    def test_transform_does_not_mutate_input(self):
        import json
        from pathlib import Path

        payload = json.loads(Path("public_input.json").read_text(encoding="utf-8"))
        snapshot = json.dumps(payload, sort_keys=True)

        call_candidate("solution.py", "transform", args=[payload])

        self.assertEqual(json.dumps(payload, sort_keys=True), snapshot)

    def test_load_payload_reads_utf8_json(self):
        import json
        from pathlib import Path

        result = call_candidate("solution.py", "load_payload", args=["public_input.json"])

        expected = json.loads(Path("public_input.json").read_text(encoding="utf-8"))
        self.assertEqual(result, expected)


if __name__ == "__main__":
    unittest.main()
