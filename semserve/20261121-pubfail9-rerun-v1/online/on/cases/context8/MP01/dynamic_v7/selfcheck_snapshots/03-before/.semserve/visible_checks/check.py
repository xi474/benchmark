import unittest

# Injected names provided by the visible-contract SDK runner.
# call_candidate(path, function, args=[...]) -> JSON value
# check_api_boundary(path, rule=..., contract_path=..., requirement_quote=..., args=...)
# CandidateCallError -> exception with .details dict

API_BOUNDARY_REQUIREMENTS = [
    {
        "target_path": "domains/fit/transform.py",
        "function": "transform",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": True,
                "contract_path": "README.md",
                "requirement_quote": "未知额外字段可忽略，但其中非有限JSON仍非法。",
            },
            "invalid_payload_type": {
                "applicable": True,
                "contract_path": "README.md",
                "requirement_quote": "仅对象/数组顶层合法；非法JSON、其他顶层类型和任意嵌套NaN/Infinity抛ValueError。",
            },
        },
    },
    {
        "target_path": "views/hard/transform.py",
        "function": "transform",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": True,
                "contract_path": "README.md",
                "requirement_quote": "未知额外字段可忽略，但其中非有限JSON仍非法。",
            },
            "invalid_payload_type": {
                "applicable": True,
                "contract_path": "README.md",
                "requirement_quote": "仅对象/数组顶层合法；非法JSON、其他顶层类型和任意嵌套NaN/Infinity抛ValueError。",
            },
        },
    },
    {
        "target_path": "views/soft/transform.py",
        "function": "transform",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": True,
                "contract_path": "README.md",
                "requirement_quote": "未知额外字段可忽略，但其中非有限JSON仍非法。",
            },
            "invalid_payload_type": {
                "applicable": True,
                "contract_path": "README.md",
                "requirement_quote": "仅对象/数组顶层合法；非法JSON、其他顶层类型和任意嵌套NaN/Infinity抛ValueError。",
            },
        },
    },
    {
        "target_path": "views/comparison/transform.py",
        "function": "transform",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": True,
                "contract_path": "README.md",
                "requirement_quote": "未知额外字段可忽略，但其中非有限JSON仍非法。",
            },
            "invalid_payload_type": {
                "applicable": True,
                "contract_path": "README.md",
                "requirement_quote": "仅对象/数组顶层合法；非法JSON、其他顶层类型和任意嵌套NaN/Infinity抛ValueError。",
            },
        },
    },
]


class TestApiBoundaries(unittest.TestCase):
    def test_transform_api_boundaries(self):
        seeds = {
            "domains/fit/transform.py": [
                {
                    "classes": ["red", "blue"],
                    "sample_weight": [1, 2],
                    "members": [
                        {
                            "id": "a",
                            "active": True,
                            "weight": 1,
                            "predictions": ["red", "blue"],
                            "classes": ["red", "blue"],
                            "probabilities": [[1.0, 0.0], [0.0, 1.0]],
                        }
                    ],
                },
                {"name": "fit", "inputs": ["x"], "output": "y"},
            ],
            "views/hard/transform.py": [
                {
                    "name": "fit",
                    "result": {
                        "classes": ["red", "blue"],
                        "sample_count": 1,
                        "members": [
                            {
                                "id": "a",
                                "active": True,
                                "weight": 1,
                                "fit_weight": [1],
                                "predictions": ["red"],
                                "classes": ["red", "blue"],
                                "probabilities": [[1.0, 0.0]],
                            }
                        ],
                    },
                },
                {"name": "hard", "inputs": ["x"], "output": "y"},
            ],
            "views/soft/transform.py": [
                {
                    "name": "fit",
                    "result": {
                        "classes": ["red", "blue"],
                        "sample_count": 1,
                        "members": [
                            {
                                "id": "a",
                                "active": True,
                                "weight": 1,
                                "fit_weight": [1],
                                "predictions": ["red"],
                                "classes": ["red", "blue"],
                                "probabilities": [[1.0, 0.0]],
                            }
                        ],
                    },
                },
                {"name": "soft", "inputs": ["x"], "output": "y"},
            ],
            "views/comparison/transform.py": [
                [
                    {"name": "hard", "result": {"predictions": ["red"]}},
                    {"name": "soft", "result": {"predictions": ["red"]}},
                ],
                {"name": "comparison", "inputs": ["x", "y"], "output": "z"},
            ],
        }
        for entry in API_BOUNDARY_REQUIREMENTS:
            target = entry["target_path"]
            args = seeds[target]
            for rule, spec in entry["rules"].items():
                with self.subTest(target=target, rule=rule):
                    if not spec["applicable"]:
                        continue
                    check_api_boundary(
                        target,
                        rule=rule,
                        contract_path=spec["contract_path"],
                        requirement_quote=spec["requirement_quote"],
                        args=args,
                    )


class TestFitMembers(unittest.TestCase):
    def test_fit_filters_inactive_and_forwards_sample_weight(self):
        payload = {
            "classes": ["red", "blue"],
            "sample_weight": [1, 2, 0, 1],
            "members": [
                {
                    "id": "a",
                    "active": True,
                    "weight": 1,
                    "predictions": ["blue", "red", "red", "blue"],
                    "classes": ["red", "blue"],
                    "probabilities": [
                        [0.2, 0.8],
                        [0.7, 0.3],
                        [0.4, 0.6],
                        [0.8, 0.2],
                    ],
                },
                {
                    "id": "b",
                    "active": False,
                    "weight": 2,
                    "predictions": ["blue", "red", "red", "blue"],
                    "classes": ["blue", "red"],
                    "probabilities": [
                        [0.8, 0.2],
                        [0.3, 0.7],
                        [0.6, 0.4],
                        [0.2, 0.8],
                    ],
                },
            ],
        }
        contract = {"name": "fit", "inputs": ["x"], "output": "y"}
        result = call_candidate(
            "domains/fit/transform.py", "transform", args=[[payload], contract]
        )
        self.assertEqual(result["name"], "fit")
        r = result["result"]
        self.assertEqual(r["classes"], ["red", "blue"])
        self.assertEqual(r["sample_count"], 4)
        self.assertEqual([m["id"] for m in r["members"]], ["a"])
        self.assertEqual(r["members"][0]["fit_weight"], [1, 2, 0, 1])

    def test_fit_rejects_inactive_only(self):
        payload = {
            "classes": ["red"],
            "sample_weight": [1],
            "members": [
                {
                    "id": "a",
                    "active": False,
                    "weight": 1,
                    "predictions": ["red"],
                    "classes": ["red"],
                    "probabilities": [[1.0]],
                }
            ],
        }
        contract = {"name": "fit", "inputs": ["x"], "output": "y"}
        with self.assertRaises(CandidateCallError) as ctx:
            call_candidate(
                "domains/fit/transform.py", "transform", args=[[payload], contract]
            )
        self.assertEqual(ctx.exception.details["failure_phase"], "candidate_exception")
        self.assertEqual(ctx.exception.details["error_type"], "ValueError")


class TestHardVote(unittest.TestCase):
    def test_hard_vote_uses_fit_weight_per_sample(self):
        fit = {
            "name": "fit",
            "result": {
                "classes": ["red", "blue"],
                "sample_count": 2,
                "members": [
                    {
                        "id": "a",
                        "active": True,
                        "weight": 1,
                        "fit_weight": [1, 0],
                        "predictions": ["red", "blue"],
                        "classes": ["red", "blue"],
                        "probabilities": [[1.0, 0.0], [0.0, 1.0]],
                    },
                    {
                        "id": "b",
                        "active": True,
                        "weight": 1,
                        "fit_weight": [0, 1],
                        "predictions": ["blue", "red"],
                        "classes": ["red", "blue"],
                        "probabilities": [[0.0, 1.0], [1.0, 0.0]],
                    },
                ],
            },
        }
        contract = {"name": "hard", "inputs": ["x"], "output": "y"}
        result = call_candidate(
            "views/hard/transform.py", "transform", args=[[fit], contract]
        )
        r = result["result"]
        self.assertEqual(r["predictions"], ["red", "red"])
        self.assertEqual(r["scores"], [[1.0, 0.0], [1.0, 0.0]])


class TestSoftVote(unittest.TestCase):
    def test_soft_vote_maps_member_class_columns(self):
        fit = {
            "name": "fit",
            "result": {
                "classes": ["red", "blue"],
                "sample_count": 1,
                "members": [
                    {
                        "id": "a",
                        "active": True,
                        "weight": 1,
                        "fit_weight": [1],
                        "predictions": ["red"],
                        "classes": ["blue", "red"],
                        "probabilities": [[0.9, 0.1]],
                    }
                ],
            },
        }
        contract = {"name": "soft", "inputs": ["x"], "output": "y"}
        result = call_candidate(
            "views/soft/transform.py", "transform", args=[[fit], contract]
        )
        r = result["result"]
        # member classes order [blue, red]; prob [0.9, 0.1] -> blue=0.9, red=0.1
        self.assertEqual(r["predictions"], ["blue"])
        self.assertEqual(r["probabilities"], [[0.1, 0.9]])


class TestComparison(unittest.TestCase):
    def test_comparison_disagreements(self):
        hard = {"name": "hard", "result": {"predictions": ["red", "blue"]}}
        soft = {"name": "soft", "result": {"predictions": ["red", "red"]}}
        contract = {"name": "comparison", "inputs": ["x", "y"], "output": "z"}
        result = call_candidate(
            "views/comparison/transform.py",
            "transform",
            args=[[hard, soft], contract],
        )
        r = result["result"]
        self.assertEqual(r["hard"], ["red", "blue"])
        self.assertEqual(r["soft"], ["red", "red"])
        self.assertEqual(r["disagreements"], [1])

    def test_comparison_rejects_mismatched_samples(self):
        hard = {"name": "hard", "result": {"predictions": ["red"]}}
        soft = {"name": "soft", "result": {"predictions": ["red", "blue"]}}
        contract = {"name": "comparison", "inputs": ["x", "y"], "output": "z"}
        with self.assertRaises(CandidateCallError) as ctx:
            call_candidate(
                "views/comparison/transform.py",
                "transform",
                args=[[hard, soft], contract],
            )
        self.assertEqual(ctx.exception.details["failure_phase"], "candidate_exception")
        self.assertEqual(ctx.exception.details["error_type"], "ValueError")


if __name__ == "__main__":
    unittest.main()
