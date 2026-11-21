import unittest

API_BOUNDARY_REQUIREMENTS = [
    {
        "target_path": "domains/index/transform.py",
        "function": "transform",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": True,
                "contract_path": "README.md",
                "requirement_quote": "未知额外字段可忽略，但其中非有限JSON仍非法。",
                "args": [
                    {
                        "columns": ["a"],
                        "pieces": [
                            {
                                "id": "p0",
                                "coordinates": [0],
                                "data": [[1]],
                                "attrs": {},
                            }
                        ],
                        "attribute_policy": "first",
                    },
                    {"name": "index", "operation": "segment_index", "inputs": ["x"]},
                ],
            },
            "invalid_payload_type": {
                "applicable": True,
                "contract_path": "README.md",
                "requirement_quote": "仅对象/数组顶层合法；非法JSON、其他顶层类型和任意嵌套NaN/Infinity抛ValueError。",
                "args": [
                    {
                        "columns": ["a"],
                        "pieces": [
                            {
                                "id": "p0",
                                "coordinates": [0],
                                "data": [[1]],
                                "attrs": {},
                            }
                        ],
                        "attribute_policy": "first",
                    },
                    {"name": "index", "operation": "segment_index", "inputs": ["x"]},
                ],
            },
        },
    },
    {
        "target_path": "domains/attributes/transform.py",
        "function": "transform",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": True,
                "contract_path": "README.md",
                "requirement_quote": "未知额外字段可忽略，但其中非有限JSON仍非法。",
                "args": [
                    {
                        "columns": ["a"],
                        "pieces": [
                            {
                                "id": "p0",
                                "coordinates": [0],
                                "data": [[1]],
                                "attrs": {"site": "0"},
                            }
                        ],
                        "attribute_policy": "first",
                    },
                    {"name": "attributes", "operation": "segment_attributes", "inputs": ["x"]},
                ],
            },
            "invalid_payload_type": {
                "applicable": True,
                "contract_path": "README.md",
                "requirement_quote": "仅对象/数组顶层合法；非法JSON、其他顶层类型和任意嵌套NaN/Infinity抛ValueError。",
                "args": [
                    {
                        "columns": ["a"],
                        "pieces": [
                            {
                                "id": "p0",
                                "coordinates": [0],
                                "data": [[1]],
                                "attrs": {"site": "0"},
                            }
                        ],
                        "attribute_policy": "first",
                    },
                    {"name": "attributes", "operation": "segment_attributes", "inputs": ["x"]},
                ],
            },
        },
    },
    {
        "target_path": "views/table/transform.py",
        "function": "transform",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": True,
                "contract_path": "README.md",
                "requirement_quote": "未知额外字段可忽略，但其中非有限JSON仍非法。",
                "args": [
                    {
                        "columns": ["a"],
                        "pieces": [
                            {
                                "id": "p0",
                                "coordinates": [0],
                                "data": [[1]],
                                "attrs": {},
                            }
                        ],
                        "attribute_policy": "first",
                    },
                    {"columns": ["a"], "order": [{"coordinate": 0, "piece": "p0", "row": 0}]},
                    {"attrs": {}, "conflicts": []},
                    {"name": "table", "operation": "segment_assemble", "inputs": ["a", "b", "c"]},
                ],
            },
            "invalid_payload_type": {
                "applicable": True,
                "contract_path": "README.md",
                "requirement_quote": "仅对象/数组顶层合法；非法JSON、其他顶层类型和任意嵌套NaN/Infinity抛ValueError。",
                "args": [
                    {
                        "columns": ["a"],
                        "pieces": [
                            {
                                "id": "p0",
                                "coordinates": [0],
                                "data": [[1]],
                                "attrs": {},
                            }
                        ],
                        "attribute_policy": "first",
                    },
                    {"columns": ["a"], "order": [{"coordinate": 0, "piece": "p0", "row": 0}]},
                    {"attrs": {}, "conflicts": []},
                    {"name": "table", "operation": "segment_assemble", "inputs": ["a", "b", "c"]},
                ],
            },
        },
    },
]


class TestApiBoundaries(unittest.TestCase):
    def test_api_boundary_rules(self):
        for entry in API_BOUNDARY_REQUIREMENTS:
            target = entry["target_path"]
            for rule, spec in entry["rules"].items():
                with self.subTest(target=target, rule=rule):
                    if not spec["applicable"]:
                        continue
                    check_api_boundary(
                        target,
                        rule=rule,
                        contract_path=spec["contract_path"],
                        requirement_quote=spec["requirement_quote"],
                        args=spec["args"],
                    )


class TestSegmentIndex(unittest.TestCase):
    def _contract(self):
        return {"name": "index", "operation": "segment_index", "inputs": ["x"]}

    def test_order_sorted_and_rows(self):
        payload = {
            "columns": ["a", "b"],
            "pieces": [
                {"id": "p0", "coordinates": [2, 0], "data": [[20, 21], [0, 1]], "attrs": {}},
                {"id": "p1", "coordinates": [3, 1], "data": [[30, 31], [10, 11]], "attrs": {}},
            ],
            "attribute_policy": "first",
        }
        result = call_candidate(
            "domains/index/transform.py", "transform", args=[[payload], self._contract()]
        )
        self.assertEqual(result["name"], "index")
        r = result["result"]
        self.assertEqual(r["columns"], ["a", "b"])
        coords = [e["coordinate"] for e in r["order"]]
        self.assertEqual(coords, [0, 1, 2, 3])
        self.assertEqual(r["order"][0], {"coordinate": 0, "piece": "p0", "row": 1})
        self.assertEqual(r["order"][3], {"coordinate": 3, "piece": "p1", "row": 0})

    def test_overlapping_coordinate_raises(self):
        payload = {
            "columns": ["a"],
            "pieces": [
                {"id": "p0", "coordinates": [1], "data": [[1]], "attrs": {}},
                {"id": "p1", "coordinates": [1], "data": [[2]], "attrs": {}},
            ],
            "attribute_policy": "first",
        }
        with self.assertRaises(CandidateCallError) as cm:
            call_candidate(
                "domains/index/transform.py", "transform", args=[[payload], self._contract()]
            )
        self.assertEqual(cm.exception.details["failure_phase"], "candidate_exception")
        self.assertEqual(cm.exception.details["error_type"], "ValueError")


class TestSegmentAttributes(unittest.TestCase):
    def _contract(self):
        return {"name": "attributes", "operation": "segment_attributes", "inputs": ["x"]}

    def test_drop_conflicts(self):
        payload = {
            "columns": ["a"],
            "pieces": [
                {"id": "p0", "coordinates": [0], "data": [[0]], "attrs": {"site": "0", "unit": "m"}},
                {"id": "p1", "coordinates": [1], "data": [[1]], "attrs": {"site": "1", "unit": "m"}},
            ],
            "attribute_policy": "drop_conflicts",
        }
        result = call_candidate(
            "domains/attributes/transform.py", "transform", args=[[payload], self._contract()]
        )
        r = result["result"]
        self.assertEqual(r["attrs"], {"unit": "m"})
        self.assertEqual(r["conflicts"], ["site"])

    def test_first_policy(self):
        payload = {
            "columns": ["a"],
            "pieces": [
                {"id": "p0", "coordinates": [0], "data": [[0]], "attrs": {"site": "0"}},
                {"id": "p1", "coordinates": [1], "data": [[1]], "attrs": {"site": "1"}},
            ],
            "attribute_policy": "first",
        }
        result = call_candidate(
            "domains/attributes/transform.py", "transform", args=[[payload], self._contract()]
        )
        r = result["result"]
        self.assertEqual(r["attrs"], {"site": "0"})
        self.assertEqual(r["conflicts"], [])


class TestSegmentAssemble(unittest.TestCase):
    def _contract(self):
        return {"name": "table", "operation": "segment_assemble", "inputs": ["a", "b", "c"]}

    def test_assemble_uses_upstream_order(self):
        original = {
            "columns": ["a", "b"],
            "pieces": [
                {"id": "p0", "coordinates": [2, 0], "data": [[20, 21], [0, 1]], "attrs": {}},
                {"id": "p1", "coordinates": [3, 1], "data": [[30, 31], [10, 11]], "attrs": {}},
            ],
            "attribute_policy": "first",
        }
        index = {
            "columns": ["a", "b"],
            "order": [
                {"coordinate": 0, "piece": "p0", "row": 1},
                {"coordinate": 1, "piece": "p1", "row": 1},
                {"coordinate": 2, "piece": "p0", "row": 0},
                {"coordinate": 3, "piece": "p1", "row": 0},
            ],
        }
        attributes = {"attrs": {"unit": "m"}, "conflicts": ["site"]}
        result = call_candidate(
            "views/table/transform.py",
            "transform",
            args=[[original, index, attributes], self._contract()],
        )
        r = result["result"]
        self.assertEqual(r["coordinates"], [0, 1, 2, 3])
        self.assertEqual(r["columns"], ["a", "b"])
        self.assertEqual(r["data"], [[0, 1], [10, 11], [20, 21], [30, 31]])
        self.assertEqual(r["attrs"], {"unit": "m"})
        self.assertEqual(r["attribute_conflicts"], ["site"])


if __name__ == "__main__":
    unittest.main()
