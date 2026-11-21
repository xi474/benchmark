import unittest


class TestTransform(unittest.TestCase):
    def _call(self, payload):
        return call_candidate("solution.py", "transform", args=[payload])

    def test_empty_topics(self):
        payload = {"topics": [], "papers": [], "graph": [["b", "r", "a"], ["a", "r", "b"]]}
        result = self._call(payload)
        self.assertEqual(result["review"], [])
        self.assertEqual(result["graph"], [["a", "r", "b"], ["b", "r", "a"]])

    def test_no_complete_assignment_returns_null(self):
        payload = {
            "topics": ["t1", "t2"],
            "papers": [
                {"id": "p0", "methods": ["m"], "claims": [["t1", "m", 5]]},
            ],
            "graph": [],
        }
        self.assertIsNone(self._call(payload))

    def test_section_not_in_methods_ignored(self):
        payload = {
            "topics": ["t1"],
            "papers": [
                {"id": "p0", "methods": ["m"], "claims": [["t1", "other", 9], ["t1", "m", 3]]},
            ],
            "graph": [],
        }
        result = self._call(payload)
        self.assertEqual(result["review"], [["t1", "p0", 3]])

    def test_max_quality_per_topic_paper(self):
        payload = {
            "topics": ["t1"],
            "papers": [
                {"id": "p0", "methods": ["m"], "claims": [["t1", "m", 3], ["t1", "m", 7]]},
            ],
            "graph": [],
        }
        result = self._call(payload)
        self.assertEqual(result["review"], [["t1", "p0", 7]])

    def test_graph_dedup_and_sort(self):
        payload = {
            "topics": ["t1"],
            "papers": [
                {"id": "p0", "methods": ["m"], "claims": [["t1", "m", 5]]},
            ],
            "graph": [["p0", "supports", "t1"], ["x", "y", "z"], ["p0", "supports", "t1"]],
        }
        result = self._call(payload)
        self.assertEqual(
            result["graph"],
            [["p0", "supports", "t1"], ["x", "y", "z"]],
        )

    def test_min_quality_then_total_then_lexicographic(self):
        payload = {
            "topics": ["a", "b"],
            "papers": [
                {"id": "p0", "methods": ["m"], "claims": [["a", "m", 10], ["b", "m", 1]]},
                {"id": "p1", "methods": ["m"], "claims": [["a", "m", 9], ["b", "m", 9]]},
                {"id": "p2", "methods": ["m"], "claims": [["a", "m", 1], ["b", "m", 10]]},
            ],
            "graph": [],
        }
        result = self._call(payload)
        self.assertEqual(result["review"], [["a", "p0", 10], ["b", "p2", 10]])

    def test_input_not_mutated(self):
        payload = {
            "topics": ["t1"],
            "papers": [
                {"id": "p0", "methods": ["m"], "claims": [["t1", "m", 5]]},
            ],
            "graph": [["x", "y", "z"]],
        }
        snapshot = {
            "topics": list(payload["topics"]),
            "papers": [dict(p) for p in payload["papers"]],
            "graph": [list(e) for e in payload["graph"]],
        }
        self._call(payload)
        self.assertEqual(payload["topics"], snapshot["topics"])
        self.assertEqual(payload["graph"], snapshot["graph"])


if __name__ == "__main__":
    unittest.main()
