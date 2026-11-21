import json
import unittest

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent


def _load(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


class TransformContractTests(unittest.TestCase):
    """Independent visible-contract checks for solution.transform."""

    def test_public_fixture_matches_expected(self):
        payload = _load("public_input.json")
        expected = _load("public_expected.json")
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(result, expected)

    def test_empty_file_no_thumbnail_produces_no_blocks(self):
        payload = {
            "session_key_hex": "00" * 32,
            "base_nonce_hex": "00" * 12,
            "file_hex": "",
            "chunk_size": 3,
            "max_retries": 0,
            "environment": "production",
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["blocks"], [])
        self.assertEqual(result["attempts"], [])
        self.assertEqual(result["notifications"], [])
        self.assertEqual(result["failed_block"], None)
        self.assertEqual(result["file_sha256"],
                         "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")

    def test_thumbnail_with_empty_file_still_processed_first(self):
        payload = {
            "session_key_hex": "00" * 32,
            "base_nonce_hex": "00" * 12,
            "file_hex": "",
            "chunk_size": 3,
            "max_retries": 0,
            "thumbnail_hex": "ff",
            "environment": "production",
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(result["status"], "ok")
        self.assertEqual(len(result["blocks"]), 1)
        self.assertEqual(result["blocks"][0]["kind"], "thumbnail")
        self.assertEqual(result["blocks"][0]["index"], 0)
        # Thumbnail bytes are not committed to the file digest.
        self.assertEqual(result["file_sha256"],
                         "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")

    def test_corrupt_attempt_exhausts_and_stops(self):
        payload = {
            "session_key_hex": "00" * 32,
            "base_nonce_hex": "00" * 12,
            "file_hex": "61626364656667",  # abcdefg
            "chunk_size": 3,
            "max_retries": 0,
            "corrupt_attempts": {"file:0": [0]},
            "environment": "production",
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(result["status"], "verification_failed")
        self.assertEqual(result["failed_block"], "file:0")
        self.assertEqual(result["blocks"], [])
        self.assertEqual(len(result["notifications"]), 1)
        self.assertEqual(result["notifications"][0]["block"], "file:0")
        self.assertEqual(result["notifications"][0]["error"], "verification_failed")
        self.assertEqual(result["file_sha256"],
                         "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")

    def test_retry_recovers_after_corrupt_first_attempt(self):
        payload = {
            "session_key_hex": "00" * 32,
            "base_nonce_hex": "00" * 12,
            "file_hex": "616263",  # abc
            "chunk_size": 3,
            "max_retries": 1,
            "corrupt_attempts": {"file:0": [0]},
            "environment": "production",
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["failed_block"], None)
        self.assertEqual(len(result["blocks"]), 1)
        self.assertEqual(len(result["attempts"]), 2)
        self.assertEqual(result["attempts"][0]["verified"], False)
        self.assertEqual(result["attempts"][1]["verified"], True)
        # Only the first failure emits a notification.
        self.assertEqual(len(result["notifications"]), 1)
        # Nonces advance by the global attempt index.
        self.assertEqual(result["attempts"][0]["attempt"], 0)
        self.assertEqual(result["attempts"][1]["attempt"], 1)
        self.assertEqual(result["blocks"][0]["nonce_hex"], "000000000000000000000001")

    def test_file_sha256_commits_only_successful_file_blocks(self):
        payload = {
            "session_key_hex": "00" * 32,
            "base_nonce_hex": "00" * 12,
            "file_hex": "61626364656667",  # abcdefg
            "chunk_size": 3,
            "max_retries": 0,
            "corrupt_attempts": {"file:1": [0]},
            "environment": "production",
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(result["status"], "verification_failed")
        self.assertEqual(result["failed_block"], "file:1")
        # Only block 0 (abc) committed before exhaustion.
        self.assertEqual(len(result["blocks"]), 1)
        self.assertEqual(result["blocks"][0]["index"], 0)
        import hashlib
        self.assertEqual(result["file_sha256"],
                         hashlib.sha256(b"abc").hexdigest())

    def test_transform_does_not_mutate_input(self):
        payload = _load("public_input.json")
        snapshot = json.dumps(payload, sort_keys=True)
        call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(json.dumps(payload, sort_keys=True), snapshot)


if __name__ == "__main__":
    unittest.main()
