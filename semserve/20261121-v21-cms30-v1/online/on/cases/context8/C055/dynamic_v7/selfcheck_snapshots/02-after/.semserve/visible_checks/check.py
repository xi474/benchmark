import unittest

API_BOUNDARY_REQUIREMENTS = [
    {
        "target_path": "solution.py",
        "function": "transform",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": False,
                "contract_path": "TASK.md",
                "requirement_quote": "输入 sources 是按覆盖顺序的文档源序列，每份有 name、trusted、yaml。",
                "reason": "The visible contract does not state that unknown fields or non-finite numbers must raise ValueError.",
            },
            "invalid_payload_type": {
                "applicable": False,
                "contract_path": "TASK.md",
                "requirement_quote": "输入 sources 是按覆盖顺序的文档源序列，每份有 name、trusted、yaml。",
                "reason": "The visible contract does not state that a non-object payload must raise ValueError.",
            },
        },
    },
]


class VisibleContractTests(unittest.TestCase):
    def test_transform_public_fixture(self):
        # Output contract: status, entries, dump for the public input.
        result = call_candidate("solution.py", "transform", args=[{
            "sources": [
                {"name": "base", "trusted": True, "yaml": "x: &base first\ny: *base\nz: see-${x}\n"},
                {"name": "override", "trusted": False, "yaml": "x: plain-${y}\n"},
            ],
            "tags": True,
            "keys": {},
        }])
        self.assertEqual(result["status"], "ok")
        self.assertIsInstance(result["entries"], list)
        self.assertIsInstance(result["dump"], str)
        self.assertEqual(result["dump"][-1], "\n")

    def test_sealed_when_missing_key(self):
        # tags=False with a vault id missing from keys -> {"status":"sealed"}.
        result = call_candidate("solution.py", "transform", args=[{
            "sources": [
                {"name": "s", "trusted": True, "yaml": "a: !vault v1\n"},
            ],
            "tags": False,
            "keys": {},
        }])
        self.assertEqual(result, {"status": "sealed"})

    def test_vault_unsealed_with_key(self):
        # tags=False with a matching key -> plaintext, trusted=True.
        result = call_candidate("solution.py", "transform", args=[{
            "sources": [
                {"name": "s", "trusted": True, "yaml": "a: !vault v1\n"},
            ],
            "tags": False,
            "keys": {"v1": "secret"},
        }])
        self.assertEqual(result["status"], "ok")
        entry = result["entries"][0]
        self.assertEqual(entry[0], "a")
        self.assertEqual(entry[3], True)
        self.assertEqual(entry[4], "secret")

    def test_vault_sealed_tags_true(self):
        # tags=True keeps ciphertext, trusted=False, render "[sealed]".
        result = call_candidate("solution.py", "transform", args=[{
            "sources": [
                {"name": "s", "trusted": True, "yaml": "a: !vault v1\n"},
            ],
            "tags": True,
            "keys": {},
        }])
        entry = result["entries"][0]
        self.assertEqual(entry[3], False)
        self.assertEqual(entry[4], "[sealed]")
        self.assertIn("!vault", result["dump"])


if __name__ == "__main__":
    unittest.main()
