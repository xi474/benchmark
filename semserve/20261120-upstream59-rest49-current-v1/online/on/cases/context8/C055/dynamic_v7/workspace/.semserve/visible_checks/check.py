import unittest

# Visible-contract self-checks for solution.py transform().
# transform(payload) takes a single positional argument.

API_BOUNDARY_REQUIREMENTS = [
    {
        "target_path": "solution.py",
        "function": "transform",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": False,
                "contract_path": "TASK.md",
                "requirement_quote": "输入 sources 是按覆盖顺序的文档源序列，每份有 name、trusted、yaml。",
                "reason": "The visible contract does not state that unknown fields or non-finite values must raise ValueError; it only describes the YAML subset and output shape.",
            },
            "invalid_payload_type": {
                "applicable": False,
                "contract_path": "TASK.md",
                "requirement_quote": "实现 solution.py 中的 transform(payload)，返回题面指定的 JSON 值并保持输入值完整。",
                "reason": "The visible contract does not specify ValueError on invalid payload types; it only requires returning the documented JSON value.",
            },
        },
    },
]


class TestTransform(unittest.TestCase):
    def test_vault_sealed_when_tags_true(self):
        # tags=true: vault exported as ciphertext, trusted=false, render "[sealed]".
        payload = {
            "sources": [
                {"name": "s", "trusted": True, "yaml": "k: !vault abc123\n"},
            ],
            "tags": True,
            "keys": {},
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["entries"][0][3], False)
        self.assertEqual(result["entries"][0][4], "[sealed]")
        self.assertIn("!vault", result["dump"])

    def test_vault_unsealed_when_tags_false(self):
        # tags=false: plaintext from keys, trusted=true.
        payload = {
            "sources": [
                {"name": "s", "trusted": True, "yaml": "k: !vault abc123\n"},
            ],
            "tags": False,
            "keys": {"abc123": "secret"},
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["entries"][0][3], True)
        self.assertEqual(result["entries"][0][4], "secret")

    def test_vault_missing_key_returns_sealed(self):
        payload = {
            "sources": [
                {"name": "s", "trusted": True, "yaml": "k: !vault abc123\n"},
            ],
            "tags": False,
            "keys": {},
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(result, {"status": "sealed"})

    def test_alias_snapshot_keeps_anchor_position(self):
        # alias value origin is the anchor's position, not the alias line.
        payload = {
            "sources": [
                {"name": "s", "trusted": True,
                 "yaml": "a: &x hello\nb: *x\n"},
            ],
            "tags": True,
            "keys": {},
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        b_entry = [e for e in result["entries"] if e[0] == "b"][0]
        self.assertEqual(b_entry[2], ["s", 1, 4])  # anchor value position

    def test_untrusted_value_keeps_literal_template(self):
        # untrusted normal value keeps original text (no expansion).
        payload = {
            "sources": [
                {"name": "s", "trusted": False, "yaml": "a: x-${b}\n"},
                {"name": "t", "trusted": True, "yaml": "b: hello\n"},
            ],
            "tags": True,
            "keys": {},
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        a_entry = [e for e in result["entries"] if e[0] == "a"][0]
        self.assertEqual(a_entry[4], "x-${b}")

    def test_trusted_value_expands_recursively(self):
        payload = {
            "sources": [
                {"name": "s", "trusted": True,
                 "yaml": "a: ${b}\nb: ${c}\nc: done\n"},
            ],
            "tags": True,
            "keys": {},
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        a_entry = [e for e in result["entries"] if e[0] == "a"][0]
        self.assertEqual(a_entry[4], "done")

    def test_entries_sorted_by_key(self):
        payload = {
            "sources": [
                {"name": "s", "trusted": True,
                 "yaml": "z: 1\na: 2\nm: 3\n"},
            ],
            "tags": True,
            "keys": {},
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        keys = [e[0] for e in result["entries"]]
        self.assertEqual(keys, sorted(keys))
        self.assertEqual(keys, ["a", "m", "z"])


if __name__ == "__main__":
    unittest.main()
