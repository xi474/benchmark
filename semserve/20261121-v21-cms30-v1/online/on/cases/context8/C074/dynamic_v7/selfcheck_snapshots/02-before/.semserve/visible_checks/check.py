import unittest

try:
    from visible_contract_check_sdk import call_candidate, CandidateCallError, check_api_boundary
except Exception:  # pragma: no cover
    call_candidate = None
    CandidateCallError = Exception
    check_api_boundary = None


class TestTransformBehavior(unittest.TestCase):
    """Independent behavior checks for the multi-mount sync transform."""

    def test_public_fixture_result(self):
        payload = {
            "nodes": {
                "root": {"files": {"old": "1"}, "dirs": {"d": "disk", "mirror": "disk"}, "ignore": []},
                "disk": {"files": {"intro": "2", "end": "3"}, "dirs": {}, "ignore": []},
            },
            "mounts": {"A": "root", "B": "disk"},
            "initial": {
                "A/old": "1",
                "A/d/intro": "2",
                "A/d/gone": "4",
                "A/mirror/intro": "2",
                "B/intro": "2",
            },
            "scans": [{"finish": ["A/d", "B"], "replace": {}}],
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["index"]["A/d/end"], "3")
        self.assertEqual(result[0]["index"]["B/end"], "3")
        self.assertNotIn("A/d/gone", result[0]["index"])
        self.assertEqual(result[0]["changed"]["4"], [["A/d/gone"], []])
        self.assertEqual(result[0]["changed"]["3"], [[], ["A/d/end", "B/end"]])

    def test_ignore_prunes_branch(self):
        payload = {
            "nodes": {
                "root": {"files": {}, "dirs": {"d": "disk"}, "ignore": []},
                "disk": {"files": {"a": "1"}, "dirs": {"sub": "sub"}, "ignore": ["sub"]},
                "sub": {"files": {"x": "9"}, "dirs": {}, "ignore": []},
            },
            "mounts": {"A": "root"},
            "initial": {"A/d/sub/x": "9", "A/d/a": "1"},
            "scans": [{"finish": ["A/d"], "replace": {}}],
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertNotIn("A/d/sub/x", result[0]["index"])
        self.assertIn("A/d/a", result[0]["index"])
        self.assertEqual(result[0]["changed"]["9"], [["A/d/sub/x"], []])

    def test_replace_accumulates(self):
        payload = {
            "nodes": {
                "root": {"files": {}, "dirs": {"d": "disk"}, "ignore": []},
                "disk": {"files": {"a": "1"}, "dirs": {}, "ignore": []},
            },
            "mounts": {"A": "root"},
            "initial": {},
            "scans": [
                {"finish": ["A/d"], "replace": {"disk": {"files": {"b": "2"}, "dirs": {}, "ignore": []}}},
                {"finish": ["A/d"], "replace": {}},
            ],
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(result[0]["index"], {"A/d/b": "2"})
        self.assertEqual(result[1]["index"], {"A/d/b": "2"})

    def test_unfinished_subdir_preserved(self):
        payload = {
            "nodes": {
                "root": {"files": {}, "dirs": {"d": "disk"}, "ignore": []},
                "disk": {"files": {}, "dirs": {"sub": "sub"}, "ignore": []},
                "sub": {"files": {"x": "9"}, "dirs": {}, "ignore": []},
            },
            "mounts": {"A": "root"},
            "initial": {"A/d/sub/x": "9"},
            "scans": [{"finish": ["A/d"], "replace": {}}],
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertIn("A/d/sub/x", result[0]["index"])


if __name__ == "__main__":
    unittest.main()
