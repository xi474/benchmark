import unittest

API_BOUNDARY_REQUIREMENTS = [
    {
        "target_path": "solution.py",
        "function": "transform",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": False,
                "contract_path": "TASK.md",
                "requirement_quote": "验收覆盖本文正常输入域与完整交付，不要求额外NaN/Infinity防御",
                "reason": "The public contract explicitly excludes NaN/Infinity defense.",
            },
            "invalid_payload_type": {
                "applicable": False,
                "contract_path": "TASK.md",
                "requirement_quote": "验收覆盖本文正常输入域与完整交付，不要求额外NaN/Infinity防御",
                "reason": "The contract does not require ValueError on invalid payload types.",
            },
        },
    },
]


class TestTransformContract(unittest.TestCase):
    def test_transform_returns_expected_shape(self):
        payload = {
            "steps": [
                {"keys": ["printf 'X\\n'", "Enter"], "until": "PROMPT> "}
            ]
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertIsInstance(result, dict)
        self.assertIn("chunks", result)
        self.assertIn("closed", result)
        self.assertIsInstance(result["chunks"], list)
        self.assertIsInstance(result["closed"], bool)

    def test_transform_does_not_mutate_input(self):
        payload = {
            "steps": [
                {"keys": ["printf 'X\\n'", "Enter"], "until": "PROMPT> "}
            ]
        }
        snapshot = __import__("json").dumps(payload, sort_keys=True)
        call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(__import__("json").dumps(payload, sort_keys=True), snapshot)

    def test_key_sequences_encoding(self):
        payload = {
            "steps": [
                {"keys": ["Enter", "C-c", "C-d", "C-u", "Tab", "Backspace", "ab"]}
            ]
        }
        result = call_candidate(
            "components/key_sequences/work.py", "compute", args=[payload]
        )
        self.assertEqual(result, ["0d030415097f6162"])

    def test_session_config_defaults(self):
        payload = {"steps": [{"keys": ["x"], "until": None}]}
        result = call_candidate(
            "components/session_config/work.py", "compute", args=[payload]
        )
        self.assertEqual(result["timeout"], 4)
        self.assertEqual(result["markers"], [None])
        self.assertIn("PS1='PROMPT> '", result["rc"])
        self.assertIn("PS2='CONT> '", result["rc"])
        self.assertIn("HISTFILE=/dev/null", result["rc"])

    def test_session_config_startup_appended(self):
        payload = {
            "startup": "echo hello",
            "steps": [{"keys": ["x"], "until": "PROMPT> "}],
        }
        result = call_candidate(
            "components/session_config/work.py", "compute", args=[payload]
        )
        self.assertTrue(result["rc"].endswith("echo hello\n"))


if __name__ == "__main__":
    unittest.main()
