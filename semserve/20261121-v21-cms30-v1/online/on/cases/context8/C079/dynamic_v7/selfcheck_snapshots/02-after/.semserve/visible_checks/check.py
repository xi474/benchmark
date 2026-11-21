import json
import unittest
from pathlib import Path


def _payload():
    return json.loads(Path("public_input.json").read_text(encoding="utf-8"))


def _expected():
    return json.loads(Path("public_expected.json").read_text(encoding="utf-8"))


class TestTransformContract(unittest.TestCase):
    def test_public_fixture_matches_expected(self):
        result = call_candidate("solution.py", "transform", args=[_payload()])
        self.assertEqual(result, _expected())

    def test_empty_file_no_thumbnail_produces_no_blocks(self):
        payload = {
            "session_key_hex": "01" * 32,
            "base_nonce_hex": "00" * 12,
            "chunk_size": 3,
            "file_hex": "",
            "max_retries": 0,
            "environment": "production",
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["blocks"], [])
        self.assertEqual(result["attempts"], [])
        self.assertEqual(result["notifications"], [])
        self.assertEqual(result["failed_block"], None)
        self.assertEqual(result["file_sha256"], "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")

    def test_thumbnail_present_empty_file_still_processed(self):
        payload = {
            "session_key_hex": "01" * 32,
            "base_nonce_hex": "00" * 12,
            "chunk_size": 3,
            "file_hex": "",
            "thumbnail_hex": "aabb",
            "max_retries": 0,
            "environment": "production",
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(result["status"], "ok")
        self.assertEqual(len(result["blocks"]), 1)
        self.assertEqual(result["blocks"][0]["kind"], "thumbnail")
        self.assertEqual(result["blocks"][0]["index"], 0)
        self.assertEqual(result["file_sha256"], "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")

    def test_corrupt_attempt_causes_retry_and_success(self):
        payload = {
            "session_key_hex": "01" * 32,
            "base_nonce_hex": "00" * 12,
            "chunk_size": 3,
            "file_hex": "616263",
            "max_retries": 1,
            "corrupt_attempts": {"file:0": [0]},
            "environment": "production",
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["failed_block"], None)
        self.assertEqual(result["attempts"][0]["verified"], False)
        self.assertEqual(result["attempts"][1]["verified"], True)
        self.assertEqual(len(result["notifications"]), 1)
        self.assertEqual(result["notifications"][0]["block"], "file:0")
        self.assertEqual(result["notifications"][0]["error"], "verification_failed")
        self.assertEqual(len(result["blocks"]), 1)
        self.assertEqual(result["blocks"][0]["plaintext_sha256"],
                         "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad")

    def test_exhausted_retries_stop_and_report_failed_block(self):
        payload = {
            "session_key_hex": "01" * 32,
            "base_nonce_hex": "00" * 12,
            "chunk_size": 3,
            "file_hex": "616263646566",
            "max_retries": 0,
            "corrupt_attempts": {"file:0": [0]},
            "environment": "production",
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(result["status"], "verification_failed")
        self.assertEqual(result["failed_block"], "file:0")
        self.assertEqual(len(result["attempts"]), 1)
        self.assertEqual(result["attempts"][0]["verified"], False)
        self.assertEqual(result["blocks"], [])
        self.assertEqual(len(result["notifications"]), 1)
        self.assertEqual(result["file_sha256"], "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")

    def test_input_not_mutated(self):
        payload = _payload()
        snapshot = json.dumps(payload, sort_keys=True)
        call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(json.dumps(payload, sort_keys=True), snapshot)


if __name__ == "__main__":
    unittest.main()
