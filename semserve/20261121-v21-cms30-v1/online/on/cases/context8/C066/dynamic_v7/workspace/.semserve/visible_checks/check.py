import unittest

API_BOUNDARY_REQUIREMENTS = [
    {
        "target_path": "solution.py",
        "function": "transform",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": False,
                "contract_path": "TASK.md",
                "requirement_quote": "initial 是 {主键: {body,rank}}，其中 body 为字符串或 null，rank 为整数或 null。",
                "reason": "The public spec does not state that unknown fields or non-finite values must raise ValueError.",
            },
            "invalid_payload_type": {
                "applicable": False,
                "contract_path": "TASK.md",
                "requirement_quote": "实现 solution.py 中的 transform(payload)，返回题面指定的 JSON 值并保持输入值完整。",
                "reason": "The public spec does not state that a non-object payload must raise ValueError.",
            },
        },
    },
]


class TransformBehaviorTests(unittest.TestCase):
    def test_commit_primary_key_swap(self):
        payload = {
            "initial": {
                "a": {"body": "one", "rank": 1},
                "b": {"body": "", "rank": 2},
            },
            "txs": [
                {
                    "lsn": 1,
                    "statements": [
                        [
                            {"op": "U", "old": "a", "cols": [{"name": "key", "type": "text", "value": "b"}]},
                            {"op": "U", "old": "b", "cols": [{"name": "key", "type": "text", "value": "a"}, {"name": "body", "type": "text", "value": None}]},
                        ]
                    ],
                }
            ],
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(result["log"], [[1, "COMMIT"]])
        self.assertEqual(result["rows"], {
            "b": {"body": "one", "rank": 1},
            "a": {"body": None, "rank": 2},
        })

    def test_abort_missing_old_rolls_back(self):
        payload = {
            "initial": {"a": {"body": "x", "rank": 1}},
            "txs": [
                {
                    "lsn": 1,
                    "statements": [
                        [{"op": "U", "old": "a", "cols": [{"name": "body", "type": "text", "value": "y"}]}],
                        [{"op": "U", "old": "zzz", "cols": [{"name": "body", "type": "text", "value": "w"}]}],
                    ],
                }
            ],
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(result["log"], [[1, "ABORT"]])
        self.assertEqual(result["rows"], {"a": {"body": "x", "rank": 1}})

    def test_replay_committed_lsn(self):
        payload = {
            "initial": {"a": {"body": "x", "rank": 1}},
            "txs": [
                {"lsn": 1, "statements": [[{"op": "U", "old": "a", "cols": [{"name": "body", "type": "text", "value": "y"}]}]]},
                {"lsn": 1, "statements": [[{"op": "U", "old": "a", "cols": [{"name": "body", "type": "text", "value": "z"}]}]]},
            ],
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(result["log"], [[1, "COMMIT"], [1, "REPLAY"]])
        self.assertEqual(result["rows"], {"a": {"body": "y", "rank": 1}})

    def test_insert_requires_all_columns(self):
        payload = {
            "initial": {},
            "txs": [
                {
                    "lsn": 1,
                    "statements": [
                        [{"op": "I", "cols": [{"name": "key", "type": "text", "value": "k"}, {"name": "body", "type": "text", "value": "b"}]}],
                    ],
                }
            ],
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(result["log"], [[1, "ABORT"]])
        self.assertEqual(result["rows"], {})

    def test_new_key_collision_aborts(self):
        payload = {
            "initial": {"a": {"body": "x", "rank": 1}, "b": {"body": "y", "rank": 2}},
            "txs": [
                {
                    "lsn": 1,
                    "statements": [
                        [{"op": "U", "old": "a", "cols": [{"name": "key", "type": "text", "value": "b"}]}],
                    ],
                }
            ],
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(result["log"], [[1, "ABORT"]])
        self.assertEqual(result["rows"], {"a": {"body": "x", "rank": 1}, "b": {"body": "y", "rank": 2}})


if __name__ == "__main__":
    unittest.main()
