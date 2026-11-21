import unittest

from solution import transform as _transform


def _call(payload):
    # Direct in-process call for behavior checks (no sibling-import ambiguity).
    return _transform(payload)


class TestTransformBehavior(unittest.TestCase):
    def test_output_shape_and_prompt(self):
        # Public rule: chunks is the initial read plus one read per step,
        # closed indicates EOF. A minimal valid seed.
        payload = {
            "steps": [
                {"keys": ["echo hello", "Enter"], "until": "PROMPT> "}
            ]
        }
        result = _call(payload)
        self.assertIsInstance(result, dict)
        self.assertEqual(set(result.keys()), {"chunks", "closed"})
        self.assertIsInstance(result["chunks"], list)
        self.assertIsInstance(result["closed"], bool)
        self.assertEqual(len(result["chunks"]), 2)
        self.assertEqual(result["chunks"][0], "PROMPT> ")
        self.assertIn("hello", result["chunks"][1])
        self.assertTrue(result["chunks"][1].endswith("PROMPT> "))

    def test_input_not_mutated(self):
        payload = {
            "steps": [
                {"keys": ["echo x", "Enter"], "until": "PROMPT> "}
            ]
        }
        snapshot = {
            "steps": [dict(payload["steps"][0])],
        }
        _call(payload)
        self.assertEqual(payload, snapshot)

    def test_ctrl_c_does_not_break_shell(self):
        # Ctrl-C interrupts the foreground program; the shell must survive.
        payload = {
            "steps": [
                {"keys": ["sleep 30", "Enter"], "until": "PROMPT> "},
                {"keys": ["C-c"], "until": "PROMPT> "},
                {"keys": ["echo alive", "Enter"], "until": "PROMPT> "},
            ]
        }
        result = _call(payload)
        self.assertEqual(len(result["chunks"]), 4)
        self.assertIn("alive", result["chunks"][3])
        self.assertFalse(result["closed"])

    def test_ctrl_d_eof(self):
        # Ctrl-D at an empty prompt closes the shell (EOF).
        payload = {
            "steps": [
                {"keys": ["C-d"], "until": None}
            ]
        }
        result = _call(payload)
        self.assertTrue(result["closed"])


if __name__ == "__main__":
    unittest.main()
