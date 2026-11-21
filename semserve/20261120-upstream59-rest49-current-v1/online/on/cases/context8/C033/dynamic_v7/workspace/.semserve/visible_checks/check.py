import unittest

# Injected by the SDK runner; not importable in this file's own namespace.
# call_candidate, CandidateCallError, check_api_boundary are provided at runtime.

API_BOUNDARY_REQUIREMENTS = [
    {
        "target_path": "solution.py",
        "function": "transform",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": False,
                "contract_path": "TASK.md",
                "requirement_quote": "输入elf_hex为合法ELF32 little-endian ET_EXEC、EM_MIPS程序",
                "reason": "The public contract does not state that unknown fields or non-finite values must raise ValueError; it only defines the valid input domain.",
            },
            "invalid_payload_type": {
                "applicable": False,
                "contract_path": "TASK.md",
                "requirement_quote": "核心接口transform(payload)返回下述JSON结果，不修改输入对象",
                "reason": "The contract does not specify ValueError for non-object payloads; only the valid object shape is documented.",
            },
        },
    },
]


class TestTransformContract(unittest.TestCase):
    def test_public_example_exit_code(self):
        # Public rule: exit(a0 low 8 bits) -> exit_code; steps includes exit.
        import json
        with open("public_input.json", "r", encoding="utf-8") as f:
            payload = json.load(f)
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(result["exit_code"], 7)
        self.assertEqual(result["registers"][0], 0)
        self.assertEqual(result["registers"][29], 2147418112)
        self.assertEqual(result["steps"], 6)
        self.assertEqual(result["syscalls"][0]["number"], 4001)
        self.assertEqual(result["syscalls"][0]["args"], [7, 0, 0])

    def test_output_shape_and_fields(self):
        # Output contract: required fields present with declared types.
        import json
        with open("public_input.json", "r", encoding="utf-8") as f:
            payload = json.load(f)
        result = call_candidate("solution.py", "transform", args=[payload])
        for key in ("exit_code", "registers", "hi", "lo", "steps",
                    "stdout_hex", "stderr_hex", "files", "inspect", "syscalls"):
            self.assertIn(key, result)
        self.assertEqual(len(result["registers"]), 32)
        self.assertIsInstance(result["registers"], list)
        self.assertIsInstance(result["files"], dict)
        self.assertIsInstance(result["inspect"], list)
        self.assertIsInstance(result["syscalls"], list)

    def test_transform_does_not_mutate_input(self):
        # Public rule: transform must not modify the input object.
        import json
        with open("public_input.json", "r", encoding="utf-8") as f:
            payload = json.load(f)
        snapshot = json.dumps(payload, sort_keys=True)
        call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(json.dumps(payload, sort_keys=True), snapshot)


if __name__ == "__main__":
    unittest.main()
