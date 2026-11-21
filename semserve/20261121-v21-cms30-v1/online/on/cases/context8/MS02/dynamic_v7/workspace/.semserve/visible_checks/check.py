import unittest

# Injected names provided by the visible-contract SDK runner.
try:
    from visible_contract_check_sdk import call_candidate, CandidateCallError, check_api_boundary
except Exception:  # pragma: no cover - names are injected at runtime
    call_candidate = None
    CandidateCallError = Exception
    check_api_boundary = None

VISIBLE_DOC = "TASK.md"

API_BOUNDARY_REQUIREMENTS = [
    {
        "target_path": "solution.py",
        "function": "transform",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": False,
                "contract_path": VISIBLE_DOC,
                "requirement_quote": "实现 solution.py 中的 transform(payload)，返回题面指定的 JSON 值并保持输入值完整。",
                "reason": "The public spec does not state that transform must reject non-finite values or unknown fields; it only requires returning the specified JSON value.",
            },
            "invalid_payload_type": {
                "applicable": False,
                "contract_path": VISIBLE_DOC,
                "requirement_quote": "实现 solution.py 中的 transform(payload)，返回题面指定的 JSON 值并保持输入值完整。",
                "reason": "The public spec does not document a ValueError contract for invalid payload types.",
            },
        },
    },
]


class TestTransformBehavior(unittest.TestCase):
    """High-risk behavior checks derived from TASK.md, independent of the public fixture."""

    def test_empty_topics_returns_empty_review_and_original_graph(self):
        # TASK.md: 空主题表对应空综述及原图边的去重排序。
        payload = {
            "topics": [],
            "papers": [],
            "graph": [["b", "r", "a"], ["a", "r", "b"], ["b", "r", "a"]],
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(result["review"], [])
        self.assertEqual(result["graph"], [["a", "r", "b"], ["b", "r", "a"]])

    def test_infeasible_assignment_returns_null(self):
        # TASK.md: 无完整分配返回 null。One topic, one paper with no valid claim.
        payload = {
            "topics": ["t1"],
            "papers": [{"id": "p0", "methods": ["m"], "claims": [["t1", "other", 5]]}],
            "graph": [],
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertIsNone(result)

    def test_tie_break_lexicographically_smallest_paper_id_sequence(self):
        # TASK.md: 依次最大化最低质量、总质量，再取论文ID序列字典序最小解。
        payload = {
            "topics": ["t1", "t2"],
            "papers": [
                {"id": "pA", "methods": ["m"], "claims": [["t1", "m", 3], ["t2", "m", 3]]},
                {"id": "pB", "methods": ["m"], "claims": [["t1", "m", 3], ["t2", "m", 3]]},
            ],
            "graph": [],
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual([r[1] for r in result["review"]], ["pA", "pB"])

    def test_max_quality_per_topic_uses_only_valid_sections(self):
        # TASK.md: 仅支撑章节列于本论文 methods 的候选可用；同题同论文保留最大质量。
        payload = {
            "topics": ["t1"],
            "papers": [
                {
                    "id": "p0",
                    "methods": ["m"],
                    "claims": [["t1", "m", 2], ["t1", "discussion", 9]],
                }
            ],
            "graph": [],
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(result["review"], [["t1", "p0", 2]])

    def test_graph_merges_supports_edges_deduped_and_sorted(self):
        # TASK.md: 后者是既有边与每条 [论文ID,"supports",主题] 的去重并集，按三项字典序排序。
        payload = {
            "topics": ["t1"],
            "papers": [{"id": "p0", "methods": ["m"], "claims": [["t1", "m", 5]]}],
            "graph": [["p0", "supports", "t1"], ["x", "y", "z"]],
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(
            result["graph"],
            [["p0", "supports", "t1"], ["x", "y", "z"]],
        )


if __name__ == "__main__":
    unittest.main()
