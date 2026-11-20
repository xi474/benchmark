import json
import unittest
from pathlib import Path

from workspace_reward import SCORING_REVISION, task_reward


class WorkspaceRewardTests(unittest.TestCase):
    def test_published_examples(self):
        examples = json.loads(Path(__file__).with_name("examples-v1.0.json").read_bytes())
        self.assertEqual(SCORING_REVISION, "delivery-bonus-50-v1")
        for case in examples["cases"]:
            with self.subTest(case=case["id"]):
                inputs = {key: case[key] for key in ("difficulty", "passed", "total", "strict_pass", "integrity_ok")}
                self.assertEqual(str(task_reward(**inputs)), case["expected_reward"])

    def test_missing_whole_receipt_has_no_score(self):
        self.assertIsNone(task_reward(difficulty="M", passed=None, total=10, strict_pass=None, integrity_ok=None))

    def test_reject_inconsistent_strict_result(self):
        with self.assertRaises(ValueError):
            task_reward(difficulty="M", passed=9, total=10, strict_pass=True, integrity_ok=True)

    def test_regression_swepro_sp10(self):
        self.assertEqual(str(task_reward(difficulty="M", passed=101, total=105, strict_pass=False, integrity_ok=True)), "0.961905")
