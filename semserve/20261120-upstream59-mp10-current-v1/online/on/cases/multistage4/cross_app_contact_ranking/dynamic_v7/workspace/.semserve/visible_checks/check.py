import unittest

API_BOUNDARY_REQUIREMENTS = [
    {
        "target_path": "domains/groups/transform.py",
        "function": "transform",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": True,
                "contract_path": "README.md",
                "requirement_quote": "未知额外字段可忽略，但其中非有限JSON仍非法",
            },
            "invalid_payload_type": {
                "applicable": True,
                "contract_path": "README.md",
                "requirement_quote": "仅对象/数组顶层合法；非法JSON、其他顶层类型和任意嵌套NaN/Infinity抛ValueError",
            },
        },
    },
    {
        "target_path": "domains/mail/transform.py",
        "function": "transform",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": True,
                "contract_path": "README.md",
                "requirement_quote": "未知额外字段可忽略，但其中非有限JSON仍非法",
            },
            "invalid_payload_type": {
                "applicable": True,
                "contract_path": "README.md",
                "requirement_quote": "仅对象/数组顶层合法；非法JSON、其他顶层类型和任意嵌套NaN/Infinity抛ValueError",
            },
        },
    },
    {
        "target_path": "domains/calendar/transform.py",
        "function": "transform",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": True,
                "contract_path": "README.md",
                "requirement_quote": "未知额外字段可忽略，但其中非有限JSON仍非法",
            },
            "invalid_payload_type": {
                "applicable": True,
                "contract_path": "README.md",
                "requirement_quote": "仅对象/数组顶层合法；非法JSON、其他顶层类型和任意嵌套NaN/Infinity抛ValueError",
            },
        },
    },
    {
        "target_path": "views/ranking/transform.py",
        "function": "transform",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": True,
                "contract_path": "README.md",
                "requirement_quote": "未知额外字段可忽略，但其中非有限JSON仍非法",
            },
            "invalid_payload_type": {
                "applicable": True,
                "contract_path": "README.md",
                "requirement_quote": "仅对象/数组顶层合法；非法JSON、其他顶层类型和任意嵌套NaN/Infinity抛ValueError",
            },
        },
    },
]


class VisibleContractTests(unittest.TestCase):
    def test_ranking_union_and_tiebreak(self):
        snapshot = {
            "contacts": [
                {"id": "self", "age": 30},
                {"id": "a", "age": 10},
                {"id": "b", "age": 20},
                {"id": "c", "age": 20},
            ],
            "self_id": "self",
        }
        groups = {"ids": ["a", "b"]}
        mail = {"ids": ["b", "c"]}
        calendar = {"minutes": {"a": 5, "b": 5, "c": 0}}
        payloads = [snapshot, groups, mail, calendar]
        contract = {"name": "ranking", "inputs": ["x", "y", "z", "w"]}
        result = call_candidate(
            "views/ranking/transform.py", "transform", args=[payloads, contract]
        )
        self.assertEqual(result["name"], "ranking")
        ranking = result["result"]["ranking"]
        self.assertEqual([r["id"] for r in ranking], ["b", "a", "c"])
        self.assertEqual(result["result"]["winner"], "b")

    def test_calendar_clip_and_dedup(self):
        snapshot = {
            "contacts": [{"id": "self", "age": 1}, {"id": "a", "age": 2}],
            "self_id": "self",
            "window": [0, 100],
            "events": [
                {"id": "e1", "start": -10, "end": 20, "attendees": ["self", "a", "a"]},
                {"id": "e2", "start": 90, "end": 200, "attendees": ["self", "a"]},
            ],
        }
        contract = {"name": "calendar", "inputs": ["x"]}
        result = call_candidate(
            "domains/calendar/transform.py", "transform", args=[[snapshot], contract]
        )
        self.assertEqual(result["result"]["minutes"], {"a": 30})

    def test_groups_keyword_casefold(self):
        snapshot = {
            "contacts": [{"id": "self", "age": 1}, {"id": "a", "age": 2}, {"id": "b", "age": 3}],
            "self_id": "self",
            "keyword": "DINNER",
            "groups": [
                {"id": "g1", "members": ["self", "a"], "messages": ["dinner soon"]},
                {"id": "g2", "members": ["self", "b"], "messages": ["lunch"]},
            ],
        }
        contract = {"name": "groups", "inputs": ["x"]}
        result = call_candidate(
            "domains/groups/transform.py", "transform", args=[[snapshot], contract]
        )
        self.assertEqual(result["result"]["ids"], ["a"])

    def test_mail_unknown_sender_raises(self):
        snapshot = {
            "contacts": [{"id": "self", "age": 1}],
            "self_id": "self",
            "keyword": "dinner",
            "emails": [{"id": "e", "sender": "ghost", "subject": "dinner"}],
        }
        contract = {"name": "mail", "inputs": ["x"]}
        with self.assertRaises(CandidateCallError) as cm:
            call_candidate(
                "domains/mail/transform.py", "transform", args=[[snapshot], contract]
            )
        self.assertEqual(cm.exception.details["failure_phase"], "candidate_exception")
        self.assertEqual(cm.exception.details["error_type"], "ValueError")

    def test_api_boundary_probes(self):
        groups_snapshot = {
            "contacts": [{"id": "self", "age": 1}, {"id": "a", "age": 2}],
            "self_id": "self",
            "keyword": "dinner",
            "groups": [{"id": "g", "members": ["self", "a"], "messages": ["dinner"]}],
        }
        mail_snapshot = {
            "contacts": [{"id": "self", "age": 1}, {"id": "a", "age": 2}],
            "self_id": "self",
            "keyword": "dinner",
            "emails": [{"id": "e", "sender": "a", "subject": "dinner"}],
        }
        calendar_snapshot = {
            "contacts": [{"id": "self", "age": 1}, {"id": "a", "age": 2}],
            "self_id": "self",
            "window": [0, 10],
            "events": [{"id": "e", "start": 0, "end": 5, "attendees": ["self", "a"]}],
        }
        ranking_snapshot = {
            "contacts": [{"id": "self", "age": 1}, {"id": "a", "age": 2}],
            "self_id": "self",
        }
        ranking_payloads = [
            ranking_snapshot,
            {"ids": ["a"]},
            {"ids": ["a"]},
            {"minutes": {"a": 5}},
        ]

        probes = [
            ("domains/groups/transform.py", [groups_snapshot], {"name": "groups", "inputs": ["x"]}),
            ("domains/mail/transform.py", [mail_snapshot], {"name": "mail", "inputs": ["x"]}),
            ("domains/calendar/transform.py", [calendar_snapshot], {"name": "calendar", "inputs": ["x"]}),
            ("views/ranking/transform.py", ranking_payloads, {"name": "ranking", "inputs": ["a", "b", "c", "d"]}),
        ]
        for target, payloads, contract in probes:
            with self.subTest(target=target, rule="invalid_payload_type"):
                check_api_boundary(
                    target,
                    rule="invalid_payload_type",
                    contract_path="README.md",
                    requirement_quote="仅对象/数组顶层合法；非法JSON、其他顶层类型和任意嵌套NaN/Infinity抛ValueError",
                    args=[payloads, contract],
                )
            with self.subTest(target=target, rule="nonfinite_unknown_field"):
                check_api_boundary(
                    target,
                    rule="nonfinite_unknown_field",
                    contract_path="README.md",
                    requirement_quote="未知额外字段可忽略，但其中非有限JSON仍非法",
                    args=[payloads, contract],
                )


if __name__ == "__main__":
    unittest.main()
