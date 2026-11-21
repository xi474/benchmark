import unittest

API_BOUNDARY_REQUIREMENTS = [
    {
        "target_path": "engines/eu/transform.py",
        "function": "transform",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": True,
                "contract_path": "README.md",
                "requirement_quote": "非法JSON、其他顶层类型和任意嵌套NaN/Infinity抛ValueError",
                "args": [
                    [
                        {
                            "departments": [{"id": "a", "country": "DE"}],
                            "professors": [{"id": "p1", "departments": ["a"]}],
                            "students": [],
                            "as_of": "2025-08-16",
                            "eu": ["DE"],
                        }
                    ],
                    {"name": "eu", "inputs": ["inputs/case.json"]},
                ],
            },
            "invalid_payload_type": {
                "applicable": True,
                "contract_path": "README.md",
                "requirement_quote": "仅对象/数组顶层合法；非法JSON、其他顶层类型和任意嵌套NaN/Infinity抛ValueError",
                "args": [
                    [
                        {
                            "departments": [{"id": "a", "country": "DE"}],
                            "professors": [{"id": "p1", "departments": ["a"]}],
                            "students": [],
                            "as_of": "2025-08-16",
                            "eu": ["DE"],
                        }
                    ],
                    {"name": "eu", "inputs": ["inputs/case.json"]},
                ],
            },
        },
    },
    {
        "target_path": "engines/students/transform.py",
        "function": "transform",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": True,
                "contract_path": "README.md",
                "requirement_quote": "非法JSON、其他顶层类型和任意嵌套NaN/Infinity抛ValueError",
                "args": [
                    [
                        {
                            "departments": [{"id": "a", "country": "DE"}],
                            "professors": [],
                            "students": [],
                            "as_of": "2025-08-16",
                            "eu": ["DE"],
                        }
                    ],
                    {"name": "students", "inputs": ["inputs/case.json"]},
                ],
            },
            "invalid_payload_type": {
                "applicable": True,
                "contract_path": "README.md",
                "requirement_quote": "仅对象/数组顶层合法；非法JSON、其他顶层类型和任意嵌套NaN/Infinity抛ValueError",
                "args": [
                    [
                        {
                            "departments": [{"id": "a", "country": "DE"}],
                            "professors": [],
                            "students": [],
                            "as_of": "2025-08-16",
                            "eu": ["DE"],
                        }
                    ],
                    {"name": "students", "inputs": ["inputs/case.json"]},
                ],
            },
        },
    },
    {
        "target_path": "engines/countries/transform.py",
        "function": "transform",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": True,
                "contract_path": "README.md",
                "requirement_quote": "非法JSON、其他顶层类型和任意嵌套NaN/Infinity抛ValueError",
                "args": [
                    [
                        {
                            "departments": [{"id": "a", "country": "DE"}],
                            "professors": [{"id": "p1", "departments": ["a"]}],
                            "students": [],
                            "as_of": "2025-08-16",
                            "eu": ["DE"],
                        }
                    ],
                    {"name": "countries", "inputs": ["inputs/case.json"]},
                ],
            },
            "invalid_payload_type": {
                "applicable": True,
                "contract_path": "README.md",
                "requirement_quote": "仅对象/数组顶层合法；非法JSON、其他顶层类型和任意嵌套NaN/Infinity抛ValueError",
                "args": [
                    [
                        {
                            "departments": [{"id": "a", "country": "DE"}],
                            "professors": [{"id": "p1", "departments": ["a"]}],
                            "students": [],
                            "as_of": "2025-08-16",
                            "eu": ["DE"],
                        }
                    ],
                    {"name": "countries", "inputs": ["inputs/case.json"]},
                ],
            },
        },
    },
    {
        "target_path": "engines/query/transform.py",
        "function": "transform",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": True,
                "contract_path": "README.md",
                "requirement_quote": "非法JSON、其他顶层类型和任意嵌套NaN/Infinity抛ValueError",
                "args": [
                    [
                        {
                            "departments": [{"id": "a", "country": "DE"}],
                            "professors": [{"id": "p1", "departments": ["a"]}],
                            "students": [],
                            "as_of": "2025-08-16",
                            "eu": ["DE"],
                        },
                        {"name": "eu", "result": {"ids": ["p1"]}},
                        {"name": "students", "result": {"counts": {"a": 0}}},
                        {"name": "countries", "result": {"countries": {"p1": ["DE"]}}},
                    ],
                    {"name": "query", "inputs": ["x", "x", "x", "x"]},
                ],
            },
            "invalid_payload_type": {
                "applicable": True,
                "contract_path": "README.md",
                "requirement_quote": "仅对象/数组顶层合法；非法JSON、其他顶层类型和任意嵌套NaN/Infinity抛ValueError",
                "args": [
                    [
                        {
                            "departments": [{"id": "a", "country": "DE"}],
                            "professors": [{"id": "p1", "departments": ["a"]}],
                            "students": [],
                            "as_of": "2025-08-16",
                            "eu": ["DE"],
                        },
                        {"name": "eu", "result": {"ids": ["p1"]}},
                        {"name": "students", "result": {"counts": {"a": 0}}},
                        {"name": "countries", "result": {"countries": {"p1": ["DE"]}}},
                    ],
                    {"name": "query", "inputs": ["x", "x", "x", "x"]},
                ],
            },
        },
    },
]


class TestVisibleContract(unittest.TestCase):
    def test_api_boundary_rules(self):
        for req in API_BOUNDARY_REQUIREMENTS:
            for rule, spec in req["rules"].items():
                if not spec.get("applicable"):
                    continue
                with self.subTest(target=req["target_path"], rule=rule):
                    check_api_boundary(
                        req["target_path"],
                        rule=rule,
                        contract_path=spec["contract_path"],
                        requirement_quote=spec["requirement_quote"],
                        args=spec["args"],
                    )

    def test_query_consumer_behavior(self):
        payloads = [
            {
                "departments": [
                    {"id": "a", "country": "DE"},
                    {"id": "b", "country": "US"},
                    {"id": "c", "country": "FR"},
                ],
                "professors": [
                    {"id": "p47", "departments": ["a", "b"]},
                    {"id": "q47", "departments": ["a", "c"]},
                ],
                "students": [],
                "as_of": "2025-08-16",
                "eu": ["DE", "FR"],
            },
            {"name": "eu", "result": {"ids": ["p47", "q47"]}},
            {"name": "students", "result": {"counts": {"a": 6, "b": 12, "c": 6}}},
            {"name": "countries", "result": {"countries": {"p47": ["DE", "US"], "q47": ["DE", "FR"]}}},
        ]
        contract = {"name": "query", "inputs": ["x", "x", "x", "x"]}
        result = call_candidate("engines/query/transform.py", "transform", args=[payloads, contract])
        self.assertEqual(
            result,
            {
                "name": "query",
                "result": {
                    "professors": [
                        {
                            "id": "p47",
                            "countries": ["DE", "US"],
                            "eligible_departments": ["b"],
                        }
                    ]
                },
            },
        )


if __name__ == "__main__":
    unittest.main()
