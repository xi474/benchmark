import unittest

# The transform API takes a single payload object (dict). The visible contract
# (TASK.md) does not document any ValueError-on-bad-type or non-finite rejection
# rule for transform; it only specifies the business replay semantics. Both
# boundary rules are therefore classified as not applicable.
API_BOUNDARY_REQUIREMENTS = [
    {
        "target_path": "solution.py",
        "function": "transform",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": False,
                "contract_path": "TASK.md",
                "requirement_quote": "实现 solution.py 中的 transform(payload)，返回题面指定的 JSON 值并保持输入值完整。",
                "reason": "The visible contract specifies replay semantics only; it never requires transform to reject unknown fields or non-finite values with ValueError.",
            },
            "invalid_payload_type": {
                "applicable": False,
                "contract_path": "TASK.md",
                "requirement_quote": "实现 solution.py 中的 transform(payload)，返回题面指定的 JSON 值并保持输入值完整。",
                "reason": "The visible contract does not document a ValueError for a non-object payload; it only defines the replay of a payload with initial and txs.",
            },
        },
    },
]


class TransformReplayTests(unittest.TestCase):
    def test_primary_key_swap_commit(self):
        # Public rule: a statement removes all U/D old identities then places
        # I/U new rows, allowing primary-key permutation.
        payload = {
            "initial": {"a": {"body": "one", "rank": 1}, "b": {"body": "", "rank": 2}},
            "txs": [
                {
                    "lsn": 1,
                    "statements": [
                        [
                            {"op": "U", "old": "a", "cols": [{"name": "key", "type": "text", "value": "b"}]},
                            {"op": "U", "old": "b", "cols": [
                                {"name": "key", "type": "text", "value": "a"},
                                {"name": "body", "type": "text", "value": None},
                            ]},
                        ]
                    ],
                }
            ],
        }
        expected = {
            "log": [[1, "COMMIT"]],
            "rows": {
                "b": {"body": "one", "rank": 1},
                "a": {"body": None, "rank": 2},
            },
        }
        actual = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(actual, expected)

    def test_missing_old_aborts_and_rolls_back(self):
        # Public rule: a non-existent old aborts the whole transaction and
        # rolls back prior statements.
        payload = {
            "initial": {"a": {"body": "x", "rank": 1}},
            "txs": [
                {
                    "lsn": 1,
                    "statements": [
                        [
                            {"op": "U", "old": "a", "cols": [{"name": "body", "type": "text", "value": "changed"}]},
                        ],
                        [
                            {"op": "U", "old": "missing", "cols": [{"name": "body", "type": "text", "value": "y"}]},
                        ],
                    ],
                }
            ],
        }
        actual = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(actual["log"], [[1, "ABORT"]])
        self.assertEqual(actual["rows"], {"a": {"body": "x", "rank": 1}})

    def test_replay_skips_committed_lsn(self):
        # Public rule: an already-committed LSN returns REPLAY and is skipped.
        payload = {
            "initial": {},
            "txs": [
                {"lsn": 5, "statements": []},
                {"lsn": 5, "statements": []},
            ],
        }
        actual = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(actual["log"], [[5, "COMMIT"], [5, "REPLAY"]])

    def test_insert_null_body_and_rank_preserved(self):
        # Public rule: body may be null and rank may be null; explicit nulls
        # must be preserved.
        payload = {
            "initial": {},
            "txs": [
                {
                    "lsn": 1,
                    "statements": [
                        [
                            {"op": "I", "cols": [
                                {"name": "key", "type": "text", "value": "k"},
                                {"name": "body", "type": "text", "value": None},
                                {"name": "rank", "type": "int", "value": None},
                            ]},
                        ]
                    ],
                }
            ],
        }
        actual = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(actual["rows"], {"k": {"body": None, "rank": None}})

    def test_new_key_collision_aborts(self):
        # Public rule: a new-key collision aborts the whole transaction.
        # Two I ops in one statement both target key "a".
        payload = {
            "initial": {},
            "txs": [
                {
                    "lsn": 1,
                    "statements": [
                        [
                            {"op": "I", "cols": [
                                {"name": "key", "type": "text", "value": "a"},
                                {"name": "body", "type": "text", "value": "y"},
                                {"name": "rank", "type": "int", "value": "2"},
                            ]},
                            {"op": "I", "cols": [
                                {"name": "key", "type": "text", "value": "a"},
                                {"name": "body", "type": "text", "value": "z"},
                                {"name": "rank", "type": "int", "value": "3"},
                            ]},
                        ]
                    ],
                }
            ],
        }
        actual = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(actual["log"], [[1, "ABORT"]])
        self.assertEqual(actual["rows"], {})

    def test_type_marker_mismatch_aborts(self):
        # Public rule: a type-marker mismatch aborts the whole transaction.
        payload = {
            "initial": {"a": {"body": "x", "rank": 1}},
            "txs": [
                {
                    "lsn": 1,
                    "statements": [
                        [
                            {"op": "U", "old": "a", "cols": [
                                {"name": "rank", "type": "text", "value": "5"},
                            ]},
                        ]
                    ],
                }
            ],
        }
        actual = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(actual["log"], [[1, "ABORT"]])
        self.assertEqual(actual["rows"], {"a": {"body": "x", "rank": 1}})


if __name__ == "__main__":
    unittest.main()
