import unittest

API_BOUNDARY_REQUIREMENTS = [
    {
        "target_path": "playlist/transform.py",
        "function": "transform",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": True,
                "contract_path": "README.md",
                "requirement_quote": "未知额外字段可忽略，但其中非有限JSON仍非法。",
                "args": [
                    [
                        {
                            "tracks": [
                                {"id": "a", "title": "T", "artist": "A", "path": "p.mp3", "duration": 2.5}
                            ],
                            "playlist": {"id": "p", "name": "N", "track_ids": ["a"], "track_count": 1, "duration": 2.5},
                            "replacement": ["a"],
                            "criteria": {},
                        }
                    ],
                    {"name": "playlist", "operation": "playlist_replace", "inputs": ["x"], "output": "y"},
                ],
            },
            "invalid_payload_type": {
                "applicable": True,
                "contract_path": "README.md",
                "requirement_quote": "仅对象/数组顶层合法；非法JSON、其他顶层类型和任意嵌套NaN/Infinity抛ValueError。",
                "args": [
                    [
                        {
                            "tracks": [
                                {"id": "a", "title": "T", "artist": "A", "path": "p.mp3", "duration": 2.5}
                            ],
                            "playlist": {"id": "p", "name": "N", "track_ids": ["a"], "track_count": 1, "duration": 2.5},
                            "replacement": ["a"],
                            "criteria": {},
                        }
                    ],
                    {"name": "playlist", "operation": "playlist_replace", "inputs": ["x"], "output": "y"},
                ],
            },
        },
    },
    {
        "target_path": "query/transform.py",
        "function": "transform",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": True,
                "contract_path": "README.md",
                "requirement_quote": "未知额外字段可忽略，但其中非有限JSON仍非法。",
                "args": [
                    [{"criteria": {"filters": [], "limit": 10}}],
                    {"name": "query", "operation": "playlist_query", "inputs": ["x"], "output": "y"},
                ],
            },
            "invalid_payload_type": {
                "applicable": True,
                "contract_path": "README.md",
                "requirement_quote": "仅对象/数组顶层合法；非法JSON、其他顶层类型和任意嵌套NaN/Infinity抛ValueError。",
                "args": [
                    [{"criteria": {"filters": [], "limit": 10}}],
                    {"name": "query", "operation": "playlist_query", "inputs": ["x"], "output": "y"},
                ],
            },
        },
    },
    {
        "target_path": "export/transform.py",
        "function": "transform",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": True,
                "contract_path": "README.md",
                "requirement_quote": "未知额外字段可忽略，但其中非有限JSON仍非法。",
                "args": [
                    [
                        {
                            "playlist": {"id": "p", "name": "N", "track_ids": ["a"]},
                            "tracks": [
                                {"id": "a", "title": "T", "artist": "A", "path": "p.mp3", "duration": 2.5}
                            ],
                        }
                    ],
                    {"name": "export", "operation": "playlist_m3u", "inputs": ["x"], "output": "y"},
                ],
            },
            "invalid_payload_type": {
                "applicable": True,
                "contract_path": "README.md",
                "requirement_quote": "仅对象/数组顶层合法；非法JSON、其他顶层类型和任意嵌套NaN/Infinity抛ValueError。",
                "args": [
                    [
                        {
                            "playlist": {"id": "p", "name": "N", "track_ids": ["a"]},
                            "tracks": [
                                {"id": "a", "title": "T", "artist": "A", "path": "p.mp3", "duration": 2.5}
                            ],
                        }
                    ],
                    {"name": "export", "operation": "playlist_m3u", "inputs": ["x"], "output": "y"},
                ],
            },
        },
    },
]


class TestVisibleContract(unittest.TestCase):
    def test_api_boundary_rules(self):
        for entry in API_BOUNDARY_REQUIREMENTS:
            for rule, spec in entry["rules"].items():
                with self.subTest(target=entry["target_path"], rule=rule):
                    if spec["applicable"]:
                        check_api_boundary(
                            entry["target_path"],
                            rule=rule,
                            contract_path=spec["contract_path"],
                            requirement_quote=spec["requirement_quote"],
                            args=spec["args"],
                        )

    def test_playlist_replace_behavior(self):
        payload = {
            "tracks": [
                {"id": "a", "title": "T", "artist": "A", "path": "p.mp3", "duration": 2.5},
                {"id": "b", "title": "U", "artist": "B", "path": "q.mp3", "duration": 1.5},
            ],
            "playlist": {"id": "p", "name": "N", "track_ids": ["a"], "track_count": 1, "duration": 2.5},
            "replacement": ["b", "a", "b"],
            "criteria": {},
        }
        contract = {"name": "playlist", "operation": "playlist_replace", "inputs": ["x"], "output": "y"}
        result = call_candidate("playlist/transform.py", "transform", args=[[payload], contract])
        self.assertEqual(result["name"], "playlist")
        r = result["result"]
        self.assertEqual(r["playlist"]["track_ids"], ["b", "a", "b"])
        self.assertEqual(r["playlist"]["track_count"], 3)
        self.assertEqual(r["playlist"]["duration"], 5.5)
        self.assertEqual([t["id"] for t in r["tracks"]], ["b", "a", "b"])

    def test_export_m3u_rounding(self):
        payload = {
            "playlist": {"id": "p", "name": "N", "track_ids": ["a", "b"]},
            "tracks": [
                {"id": "a", "title": "T", "artist": "A", "path": "p.mp3", "duration": 2.5},
                {"id": "b", "title": "U", "artist": "B", "path": "q.mp3", "duration": 1.5},
            ],
        }
        contract = {"name": "export", "operation": "playlist_m3u", "inputs": ["x"], "output": "y"}
        result = call_candidate("export/transform.py", "transform", args=[[payload], contract])
        m3u = result["result"]["m3u"]
        self.assertTrue(m3u.startswith("#EXTM3U\n#PLAYLIST:N\n"))
        self.assertIn("#EXTINF:3,A - T\np.mp3\n", m3u)
        self.assertIn("#EXTINF:2,B - U\nq.mp3\n", m3u)

    def test_query_sql_placeholders(self):
        payload = {
            "criteria": {
                "filters": [
                    {"field": "track_count", "op": "ge", "value": 2},
                    {"field": "name", "op": "ne", "value": "O'Reilly"},
                ],
                "limit": 10,
            }
        }
        contract = {"name": "query", "operation": "playlist_query", "inputs": ["x"], "output": "y"}
        result = call_candidate("query/transform.py", "transform", args=[[payload], contract])
        r = result["result"]
        self.assertEqual(
            r["sql"],
            "SELECT id FROM playlists WHERE track_count GE ? AND name NE ? ORDER BY id LIMIT ?",
        )
        self.assertEqual(r["params"], [2, "O'Reilly", 10])


if __name__ == "__main__":
    unittest.main()
