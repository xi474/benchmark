import unittest


class TestC017VisibleContract(unittest.TestCase):
    def _run(self, payload):
        return call_candidate("solution.py", "transform", args=[payload])

    def test_conflict_rolls_back_whole_batch(self):
        payload = {
            "batches": [
                [{"email": "a@x.com", "name": "Alice", "city": "Paris",
                  "source": "web", "time": 1}],
                [{"email": "a@x.com", "name": "Alice", "city": "Rome",
                  "source": "cli", "time": 2},
                 {"email": "b@x.com", "name": "Bob", "city": "Lyon",
                  "source": "cli", "time": 3}],
            ]
        }
        result = self._run(payload)
        self.assertEqual(result["batches"][0]["status"], "committed")
        self.assertEqual(result["batches"][1]["status"], "rejected")
        self.assertEqual(result["batches"][1]["items"], [])
        emails = [r["email"] for r in result["accepted"] + result["incomplete"]]
        self.assertNotIn("b@x.com", emails)
        self.assertNotIn("b@x.com", result["sources"].get("cli", []))

    def test_incomplete_promotion_preserves_first_contact(self):
        payload = {
            "batches": [
                [{"email": "a@x.com", "name": "Alice", "city": "",
                  "source": "web", "time": 5}],
                [{"email": "a@x.com", "name": "Alice", "city": "Paris",
                  "source": "cli", "time": 9}],
            ]
        }
        result = self._run(payload)
        self.assertEqual(result["batches"][0]["items"], ["incomplete"])
        self.assertEqual(result["batches"][1]["items"], ["promoted"])
        self.assertEqual(len(result["accepted"]), 1)
        self.assertEqual(result["accepted"][0]["first_contact"], 5)
        self.assertEqual(result["accepted"][0]["city"], "Paris")
        self.assertEqual(result["incomplete"], [])

    def test_complete_record_is_immutable_duplicate(self):
        payload = {
            "batches": [
                [{"email": "a@x.com", "name": "Alice", "city": "Paris",
                  "source": "web", "time": 5}],
                [{"email": "a@x.com", "name": "Alice", "city": "Paris",
                  "source": "cli", "time": 9}],
            ]
        }
        result = self._run(payload)
        self.assertEqual(result["batches"][1]["items"], ["duplicate"])
        self.assertEqual(result["accepted"][0]["name"], "Alice")
        self.assertEqual(result["accepted"][0]["city"], "Paris")
        self.assertEqual(result["accepted"][0]["first_contact"], 5)
        self.assertEqual(result["accepted"][0]["sources"], ["cli", "web"])

    def test_empty_fields_do_not_clear_existing(self):
        payload = {
            "batches": [
                [{"email": "a@x.com", "name": "Alice", "city": "",
                  "source": "web", "time": 5}],
                [{"email": "a@x.com", "name": "", "city": "Paris",
                  "source": "cli", "time": 9}],
            ]
        }
        result = self._run(payload)
        self.assertEqual(result["accepted"][0]["name"], "Alice")
        self.assertEqual(result["accepted"][0]["city"], "Paris")

    def test_email_normalization_and_sources_sorted(self):
        payload = {
            "batches": [
                [{"email": "  A@X.COM ", "name": "Alice", "city": "Paris",
                  "source": "web", "time": 1}],
                [{"email": "a@x.com", "name": "Alice", "city": "Paris",
                  "source": "cli", "time": 2}],
            ]
        }
        result = self._run(payload)
        self.assertEqual(result["accepted"][0]["email"], "a@x.com")
        self.assertEqual(result["accepted"][0]["sources"], ["cli", "web"])
        self.assertEqual(result["sources"]["cli"], ["a@x.com"])
        self.assertEqual(result["sources"]["web"], ["a@x.com"])

    def test_input_not_mutated(self):
        payload = {
            "batches": [
                [{"email": " A@X.COM ", "name": "Alice", "city": "Paris",
                  "source": "web", "time": 1}],
            ]
        }
        snapshot = {
            "batches": [
                [dict(payload["batches"][0][0])],
            ]
        }
        self._run(payload)
        self.assertEqual(payload, snapshot)


if __name__ == "__main__":
    unittest.main()
