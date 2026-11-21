import unittest

API_BOUNDARY_REQUIREMENTS = [
    {
        "target_path": "solution.py",
        "function": "transform",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": False,
                "contract_path": "TASK.md",
                "requirement_quote": "实现 solution.py 中的 transform(payload)，返回题面指定的 JSON 值并保持输入值完整。",
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
    def test_empty_topics_returns_empty_review_and_sorted_graph(self):
        # TASK.md: 空主题表对应空综述及原图边的去重排序。
        payload = {
            "topics": [],
            "papers": [],
            "graph": [["b", "r", "c"], ["a", "r", "b"], ["b", "r", "c"]],
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(result["review"], [])
        self.assertEqual(result["graph"], [["a", "r", "b"], ["b", "r", "c"]])

    def test_infeasible_assignment_returns_null(self):
        # TASK.md: 无完整分配返回 null。
        payload = {
            "topics": ["t1", "t2"],
            "papers": [
                {"id": "p0", "methods": ["m"], "claims": [["t1", "m", 5]]},
            ],
            "graph": [],
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertIsNone(result)

    def test_tie_break_lexicographically_smallest_id_sequence(self):
        # TASK.md: 依次最大化最低质量、总质量，再取论文ID序列字典序最小解。
        payload = {
            "topics": ["t1", "t2"],
            "papers": [
                {"id": "p0", "methods": ["m"], "claims": [["t1", "m", 5], ["t2", "m", 5]]},
                {"id": "p1", "methods": ["m"], "claims": [["t1", "m", 5], ["t2", "m", 5]]},
            ],
            "graph": [],
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(result["review"], [["t1", "p0", 5], ["t2", "p1", 5]])

    def test_max_quality_per_topic_per_paper(self):
        # TASK.md: 同题同论文保留最大质量。
        payload = {
            "topics": ["t1"],
            "papers": [
                {"id": "p0", "methods": ["m"], "claims": [["t1", "m", 3], ["t1", "m", 9]]},
            ],
            "graph": [],
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(result["review"], [["t1", "p0", 9]])

    def test_invalid_section_not_used(self):
        # TASK.md: 仅支撑章节列于本论文 methods 的候选可用。
        payload = {
            "topics": ["t1"],
            "papers": [
                {"id": "p0", "methods": ["m"], "claims": [["t1", "other", 9]]},
            ],
            "graph": [],
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
