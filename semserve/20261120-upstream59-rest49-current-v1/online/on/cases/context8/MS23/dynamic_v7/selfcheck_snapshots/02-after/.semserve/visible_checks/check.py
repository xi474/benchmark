import unittest

# Injected by the visible-contract SDK runner.
try:
    from visible_contract_check_sdk import call_candidate, CandidateCallError, check_api_boundary
except Exception:
    call_candidate = None
    CandidateCallError = None
    check_api_boundary = None

TARGET = "solution.py"
VISIBLE_DOC = "TASK.md"

API_BOUNDARY_REQUIREMENTS = [
    {
        "target_path": TARGET,
        "function": "transform",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": False,
                "contract_path": VISIBLE_DOC,
                "requirement_quote": "对每个输入快照，ab[a][b]、bc[b][c]、ac[a][c] 均为非负整数人数。",
                "reason": "The visible contract does not state that unknown fields or non-finite values must raise ValueError.",
            },
            "invalid_payload_type": {
                "applicable": False,
                "contract_path": VISIBLE_DOC,
                "requirement_quote": "实现 solution.py 中的 transform(payload)，返回题面指定的 JSON 值并保持输入值完整。",
                "reason": "The visible contract does not specify ValueError for invalid payload types.",
            },
        },
    }
]


class TestTransformBehavior(unittest.TestCase):
    def test_public_fixture_matches_expected(self):
        payload = {
            "snapshots": [
                {
                    "ab": [[1, 1], [1, 1]],
                    "bc": [[1, 1], [1, 1]],
                    "ac": [[1, 1], [1, 1]],
                    "forbidden": [],
                },
                {
                    "ab": [[1, 1], [1, 1]],
                    "bc": [[1, 1], [1, 1]],
                    "ac": [[1, 1], [1, 1]],
                    "forbidden": [[1, 0, 1]],
                },
            ]
        }
        expected = [
            {
                "tables": 2,
                "spectrum": [[-2, 1], [2, 1]],
                "guaranteed": [],
                "witness": [[0, 0, 1, 1], [0, 1, 0, 1], [1, 0, 0, 1], [1, 1, 1, 1]],
            },
            {
                "tables": 1,
                "spectrum": [[-2, 1]],
                "guaranteed": [[0, 0, 1, 1], [0, 1, 0, 1], [1, 0, 0, 1], [1, 1, 1, 1]],
                "witness": [[0, 0, 1, 1], [0, 1, 0, 1], [1, 0, 0, 1], [1, 1, 1, 1]],
            },
        ]
        result = call_candidate(TARGET, "transform", args=[payload])
        self.assertEqual(result, expected)

    def test_inconsistent_totals_yield_null(self):
        # ab total = 2, bc total = 3 -> no compatible table.
        payload = {
            "snapshots": [
                {
                    "ab": [[1, 0], [1, 0]],
                    "bc": [[1, 1], [1, 0]],
                    "ac": [[1, 0], [1, 0]],
                    "forbidden": [],
                }
            ]
        }
        result = call_candidate(TARGET, "transform", args=[payload])
        self.assertEqual(result, [None])

    def test_single_customer_k2_forced(self):
        # One customer, k=2, all ratings 0 -> median 0 -> net -1.
        payload = {
            "snapshots": [
                {
                    "ab": [[1, 0], [0, 0]],
                    "bc": [[1, 0], [0, 0]],
                    "ac": [[1, 0], [0, 0]],
                    "forbidden": [],
                }
            ]
        }
        result = call_candidate(TARGET, "transform", args=[payload])
        self.assertEqual(result[0]["tables"], 1)
        self.assertEqual(result[0]["spectrum"], [[-1, 1]])
        self.assertEqual(result[0]["guaranteed"], [[0, 0, 0, 1]])
        self.assertEqual(result[0]["witness"], [[0, 0, 0, 1]])

    def test_forbidden_all_cells_yield_null(self):
        # k=2, forbid every cell -> no compatible table.
        payload = {
            "snapshots": [
                {
                    "ab": [[1, 0], [0, 0]],
                    "bc": [[1, 0], [0, 0]],
                    "ac": [[1, 0], [0, 0]],
                    "forbidden": [[0, 0, 0], [0, 0, 1], [0, 1, 0], [0, 1, 1],
                                  [1, 0, 0], [1, 0, 1], [1, 1, 0], [1, 1, 1]],
                }
            ]
        }
        result = call_candidate(TARGET, "transform", args=[payload])
        self.assertEqual(result, [None])


if __name__ == "__main__":
    unittest.main()
