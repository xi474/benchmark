import unittest

# Visible contract: TASK.md (C017). Public checks only cover the happy-path
# fixture. These tests exercise high-risk boundaries not established by the
# public fixture: batch atomicity/conflict rollback, promotion preserving
# earliest first_contact, immutable complete records, and derived source view.

API_BOUNDARY_REQUIREMENTS = [
    {
        "target_path": "solution.py",
        "function": "transform",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": False,
                "contract_path": "TASK.md",
                "requirement_quote": "只验公开输入域与核心业务约束，不验任意异常文本或编码风格。",
                "reason": "The visible contract explicitly limits validation to the public input domain and core business constraints; it does not require rejecting non-finite values in unknown fields.",
            },
            "invalid_payload_type": {
                "applicable": False,
                "contract_path": "TASK.md",
                "requirement_quote": "只验公开输入域与核心业务约束，不验任意异常文本或编码风格。",
                "reason": "The visible contract does not require ValueError on invalid payload types; it only validates the public input domain.",
            },
        },
    },
]


def _run(payload):
    return call_candidate("solution.py", "transform", args=[payload])


class TestLedgerBehavior(unittest.TestCase):
    def test_conflict_rolls_back_whole_batch(self):
        # A batch where the second record conflicts with an existing complete
        # record must be rejected atomically (items=[]), and the first record
        # of that batch must not be committed.
        payload = {
            "batches": [
                [{"email": "a@x.com", "name": "Alice", "city": "Paris",
                  "source": "web", "time": 1}],
                [{"email": "b@x.com", "name": "Bob", "city": "Rome",
                  "source": "web", "time": 2},
                 {"email": "a@x.com", "name": "Alice", "city": "London",
                  "source": "cli", "time": 3}],
            ]
        }
        result = _run(payload)
        self.assertEqual(result["batches"][0]["status"], "committed")
        self.assertEqual(result["batches"][1]["status"], "rejected")
        self.assertEqual(result["batches"][1]["items"], [])
        # b@x.com must not appear anywhere (rolled back).
        emails = [r["email"] for r in result["accepted"] + result["incomplete"]]
        self.assertNotIn("b@x.com", emails)
        # a@x.com keeps its original city (immutable complete record).
        a = [r for r in result["accepted"] if r["email"] == "a@x.com"][0]
        self.assertEqual(a["city"], "Paris")

    def test_promotion_preserves_earliest_first_contact(self):
        # Incomplete record completed later keeps the earliest first_contact.
        payload = {
            "batches": [
                [{"email": "a@x.com", "name": "Alice", "city": "",
                  "source": "web", "time": 5}],
                [{"email": "a@x.com", "name": "", "city": "Paris",
                  "source": "cli", "time": 9}],
            ]
        }
        result = _run(payload)
        self.assertEqual(result["batches"][0]["items"], ["incomplete"])
        self.assertEqual(result["batches"][1]["items"], ["promoted"])
        self.assertEqual(result["incomplete"], [])
        a = result["accepted"][0]
        self.assertEqual(a["name"], "Alice")
        self.assertEqual(a["city"], "Paris")
        self.assertEqual(a["first_contact"], 5)
        self.assertEqual(a["sources"], ["cli", "web"])

    def test_duplicate_complete_record_keeps_original_fields(self):
        # A duplicate submission of a complete record must not change
        # name/city/first_contact, but merges the source into the view.
        payload = {
            "batches": [
                [{"email": "a@x.com", "name": "Alice", "city": "Paris",
                  "source": "web", "time": 1}],
                [{"email": "a@x.com", "name": "Zed", "city": "Rome",
                  "source": "cli", "time": 99}],
            ]
        }
        result = _run(payload)
        self.assertEqual(result["batches"][1]["items"], ["duplicate"])
        a = result["accepted"][0]
        self.assertEqual(a["name"], "Alice")
        self.assertEqual(a["city"], "Paris")
        self.assertEqual(a["first_contact"], 1)
        self.assertEqual(a["sources"], ["cli", "web"])
        self.assertEqual(result["sources"]["cli"], ["a@x.com"])

    def test_sources_view_sorted_unique(self):
        # Multiple records across sources produce a sorted unique email list.
        # Use the same name/city for distinct emails so no conflict occurs.
        payload = {
            "batches": [
                [{"email": "b@x.com", "name": "Alice", "city": "Paris",
                  "source": "web", "time": 1}],
                [{"email": "a@x.com", "name": "Alice", "city": "Paris",
                  "source": "web", "time": 2}],
                [{"email": "a@x.com", "name": "Alice", "city": "Paris",
                  "source": "cli", "time": 3}],
            ]
        }
        result = _run(payload)
        self.assertEqual(result["batches"][0]["status"], "committed")
        self.assertEqual(result["batches"][1]["status"], "committed")
        self.assertEqual(result["batches"][2]["status"], "committed")
        self.assertEqual(result["sources"]["web"], ["a@x.com", "b@x.com"])
        self.assertEqual(result["sources"]["cli"], ["a@x.com"])
        # accepted sorted by email
        self.assertEqual([r["email"] for r in result["accepted"]],
                         ["a@x.com", "b@x.com"])


if __name__ == "__main__":
    unittest.main()
