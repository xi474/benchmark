import unittest
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
TASK = (ROOT / "TASK.md").read_text(encoding="utf-8")

API_BOUNDARY_REQUIREMENTS = [
    {
        "target_path": "solution.py",
        "function": "transform",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": False,
                "contract_path": str(ROOT / "TASK.md"),
                "requirement_quote": "只验公开输入域与核心业务约束，不验任意异常文本或编码风格。",
                "reason": "TASK.md explicitly limits validation to the public input domain and core business constraints; non-finite values are not part of the declared input domain.",
            },
            "invalid_payload_type": {
                "applicable": False,
                "contract_path": str(ROOT / "TASK.md"),
                "requirement_quote": "只验公开输入域与核心业务约束，不验任意异常文本或编码风格。",
                "reason": "The spec does not require ValueError on invalid payload types; it only validates the public input domain.",
            },
        },
    },
]


class TestTransform(unittest.TestCase):
    def _call(self, payload):
        return call_candidate("solution.py", "transform", args=[payload])

    def test_public_fixture(self):
        payload = json.loads((ROOT / "public_input.json").read_text(encoding="utf-8"))
        expected = json.loads((ROOT / "public_expected.json").read_text(encoding="utf-8"))
        self.assertEqual(self._call(payload), expected)

    def test_conflict_rolls_back_whole_batch(self):
        payload = {
            "batches": [
                [{"email": "a@example.com", "name": "Alice", "city": "Paris", "source": "web", "time": 1}],
                [
                    {"email": "b@example.com", "name": "Bob", "city": "Lyon", "source": "cli", "time": 2},
                    {"email": "a@example.com", "name": "Alice", "city": "Berlin", "source": "cli", "time": 3},
                ],
            ]
        }
        result = self._call(payload)
        self.assertEqual(result["batches"][1], {"status": "rejected", "items": []})
        self.assertNotIn("b@example.com", [r["email"] for r in result["accepted"]])
        self.assertNotIn("b@example.com", [r["email"] for r in result["incomplete"]])
        self.assertNotIn("b@example.com", result["sources"].get("cli", []))

    def test_promotion_preserves_first_contact(self):
        payload = {
            "batches": [
                [{"email": "a@example.com", "name": "Alice", "city": "", "source": "web", "time": 5}],
                [{"email": "a@example.com", "name": "", "city": "Paris", "source": "cli", "time": 9}],
            ]
        }
        result = self._call(payload)
        self.assertEqual(result["batches"][0]["items"], ["incomplete"])
        self.assertEqual(result["batches"][1]["items"], ["promoted"])
        self.assertEqual(result["accepted"][0]["first_contact"], 5)
        self.assertEqual(result["accepted"][0]["name"], "Alice")
        self.assertEqual(result["accepted"][0]["city"], "Paris")
        self.assertEqual(result["incomplete"], [])

    def test_empty_field_does_not_clear_existing(self):
        payload = {
            "batches": [
                [{"email": "a@example.com", "name": "Alice", "city": "Paris", "source": "web", "time": 1}],
                [{"email": "a@example.com", "name": "", "city": "", "source": "cli", "time": 2}],
            ]
        }
        result = self._call(payload)
        self.assertEqual(result["batches"][1]["items"], ["duplicate"])
        self.assertEqual(result["accepted"][0]["name"], "Alice")
        self.assertEqual(result["accepted"][0]["city"], "Paris")
        self.assertEqual(result["accepted"][0]["first_contact"], 1)

    def test_sources_merge_and_sort(self):
        payload = {
            "batches": [
                [{"email": "a@example.com", "name": "Alice", "city": "Paris", "source": "web", "time": 1}],
                [{"email": "a@example.com", "name": "Alice", "city": "Paris", "source": "cli", "time": 2}],
            ]
        }
        result = self._call(payload)
        self.assertEqual(result["accepted"][0]["sources"], ["cli", "web"])
        self.assertEqual(result["sources"]["web"], ["a@example.com"])
        self.assertEqual(result["sources"]["cli"], ["a@example.com"])

    def test_email_normalization_identity(self):
        payload = {
            "batches": [
                [{"email": " A@Example.COM ", "name": "Alice", "city": "Paris", "source": "web", "time": 1}],
                [{"email": "a@example.com", "name": "Alice", "city": "Paris", "source": "cli", "time": 2}],
            ]
        }
        result = self._call(payload)
        self.assertEqual(len(result["accepted"]), 1)
        self.assertEqual(result["accepted"][0]["email"], "a@example.com")
        self.assertEqual(result["batches"][1]["items"], ["duplicate"])

    def test_whitespace_compression(self):
        payload = {
            "batches": [
                [{"email": "a@example.com", "name": "  Alice   Smith ", "city": "  New   York ", "source": "web", "time": 1}],
            ]
        }
        result = self._call(payload)
        self.assertEqual(result["accepted"][0]["name"], "Alice Smith")
        self.assertEqual(result["accepted"][0]["city"], "New York")

    def test_output_sorted_by_email(self):
        payload = {
            "batches": [
                [
                    {"email": "z@example.com", "name": "Zed", "city": "Z", "source": "web", "time": 1},
                    {"email": "a@example.com", "name": "Amy", "city": "A", "source": "web", "time": 2},
                ]
            ]
        }
        result = self._call(payload)
        emails = [r["email"] for r in result["accepted"]]
        self.assertEqual(emails, ["a@example.com", "z@example.com"])


if __name__ == "__main__":
    unittest.main()
