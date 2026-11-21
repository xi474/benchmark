import unittest

API_BOUNDARY_REQUIREMENTS = [
    {
        "target_path": "engines/calendar/transform.py",
        "function": "transform",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": True,
                "contract_path": "README.md",
                "requirement_quote": "任意嵌套NaN/Infinity抛ValueError",
            },
            "invalid_payload_type": {
                "applicable": True,
                "contract_path": "README.md",
                "requirement_quote": "仅对象/数组顶层合法；非法JSON、其他顶层类型和任意嵌套NaN/Infinity抛ValueError",
            },
        },
    },
    {
        "target_path": "engines/invitees/transform.py",
        "function": "transform",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": True,
                "contract_path": "README.md",
                "requirement_quote": "任意嵌套NaN/Infinity抛ValueError",
            },
            "invalid_payload_type": {
                "applicable": True,
                "contract_path": "README.md",
                "requirement_quote": "仅对象/数组顶层合法；非法JSON、其他顶层类型和任意嵌套NaN/Infinity抛ValueError",
            },
        },
    },
    {
        "target_path": "engines/supplies/transform.py",
        "function": "transform",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": True,
                "contract_path": "README.md",
                "requirement_quote": "任意嵌套NaN/Infinity抛ValueError",
            },
            "invalid_payload_type": {
                "applicable": True,
                "contract_path": "README.md",
                "requirement_quote": "仅对象/数组顶层合法；非法JSON、其他顶层类型和任意嵌套NaN/Infinity抛ValueError",
            },
        },
    },
    {
        "target_path": "engines/commit/transform.py",
        "function": "transform",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": True,
                "contract_path": "README.md",
                "requirement_quote": "任意嵌套NaN/Infinity抛ValueError",
            },
            "invalid_payload_type": {
                "applicable": True,
                "contract_path": "README.md",
                "requirement_quote": "仅对象/数组顶层合法；非法JSON、其他顶层类型和任意嵌套NaN/Infinity抛ValueError",
            },
        },
    },
]


class TestCalendar(unittest.TestCase):
    def test_slots_earliest_two(self):
        payload = {
            "now": 30,
            "duration": 180,
            "gap": 60,
            "windows": [{"id": "w1", "start": 0, "end": 600}, {"id": "w2", "start": 600, "end": 1200}],
            "busy": [{"id": "b", "start": 200, "end": 300}],
        }
        contract = {"name": "calendar", "inputs": ["inputs/case.json"]}
        out = call_candidate("engines/calendar/transform.py", "transform", args=[[payload], contract])
        self.assertEqual(out["name"], "calendar")
        self.assertEqual(out["result"]["complete"], True)
        self.assertEqual(out["result"]["slots"], [{"start": 300, "end": 480}, {"start": 540, "end": 720}])


class TestInvitees(unittest.TestCase):
    def test_members_union_minus_exclude(self):
        payload = {
            "namespace": "n47",
            "groups": [
                {"id": "a", "members": ["one", "two"]},
                {"id": "b", "members": ["two", "three"]},
            ],
            "invite_groups": ["a", "b"],
            "exclude": ["one"],
        }
        contract = {"name": "invitees", "inputs": ["inputs/case.json"]}
        out = call_candidate("engines/invitees/transform.py", "transform", args=[[payload], contract])
        self.assertEqual(out["result"]["group_id"], "n47-panel")
        self.assertEqual(out["result"]["members"], ["three", "two"])


class TestSupplies(unittest.TestCase):
    def test_rating_then_price_then_id(self):
        payload = {
            "products": [
                {"id": "p1", "category": "pens", "stock": 20, "price_cents": 100, "rating": 0},
                {"id": "p2", "category": "pens", "stock": 20, "price_cents": 102, "rating": 2},
                {"id": "p3", "category": "pens", "stock": 20, "price_cents": 101, "rating": 2},
            ],
            "requirements": [{"category": "pens", "quantity": 4}],
        }
        contract = {"name": "supplies", "inputs": ["inputs/case.json"]}
        out = call_candidate("engines/supplies/transform.py", "transform", args=[[payload], contract])
        self.assertEqual(out["result"]["items"], [{"category": "pens", "id": "p3", "quantity": 4, "total_cents": 404}])
        self.assertEqual(out["result"]["unavailable"], [])


class TestCommit(unittest.TestCase):
    def test_commit_two_events(self):
        slots = {"name": "calendar", "result": {"complete": True, "slots": [{"start": 300, "end": 480}, {"start": 540, "end": 720}]}}
        invitees = {"name": "invitees", "result": {"group_id": "n47-panel", "members": ["three", "two"]}}
        supplies = {"name": "supplies", "result": {"items": [], "unavailable": []}}
        contract = {"name": "commit", "inputs": ["outputs/calendar.json", "outputs/invitees.json", "outputs/supplies.json"]}
        out = call_candidate("engines/commit/transform.py", "transform", args=[[slots, invitees, supplies], contract])
        self.assertEqual(out["result"]["events"][0]["id"], "n47-panel-1")
        self.assertEqual(out["result"]["events"][1]["id"], "n47-panel-2")
        self.assertEqual(out["result"]["notification"]["event_ids"], ["n47-panel-1", "n47-panel-2"])


class TestApiBoundary(unittest.TestCase):
    def test_boundary_probes(self):
        calendar_payload = {
            "now": 30, "duration": 180, "gap": 60,
            "windows": [{"id": "w1", "start": 0, "end": 600}],
            "busy": [],
        }
        invitees_payload = {
            "namespace": "n", "groups": [{"id": "a", "members": ["x"]}],
            "invite_groups": ["a"], "exclude": [],
        }
        supplies_payload = {
            "products": [{"id": "p", "category": "c", "stock": 1, "price_cents": 1, "rating": 0}],
            "requirements": [{"category": "c", "quantity": 1}],
        }
        commit_payloads = [
            {"complete": True, "slots": [{"start": 0, "end": 1}, {"start": 2, "end": 3}]},
            {"group_id": "g-panel", "members": ["x"]},
            {"items": [], "unavailable": []},
        ]

        probes = [
            ("engines/calendar/transform.py", "nonfinite_unknown_field", [calendar_payload, {"name": "calendar", "inputs": ["inputs/case.json"]}]),
            ("engines/calendar/transform.py", "invalid_payload_type", [calendar_payload, {"name": "calendar", "inputs": ["inputs/case.json"]}]),
            ("engines/invitees/transform.py", "nonfinite_unknown_field", [invitees_payload, {"name": "invitees", "inputs": ["inputs/case.json"]}]),
            ("engines/invitees/transform.py", "invalid_payload_type", [invitees_payload, {"name": "invitees", "inputs": ["inputs/case.json"]}]),
            ("engines/supplies/transform.py", "nonfinite_unknown_field", [supplies_payload, {"name": "supplies", "inputs": ["inputs/case.json"]}]),
            ("engines/supplies/transform.py", "invalid_payload_type", [supplies_payload, {"name": "supplies", "inputs": ["inputs/case.json"]}]),
            ("engines/commit/transform.py", "nonfinite_unknown_field", [commit_payloads, {"name": "commit", "inputs": ["outputs/calendar.json", "outputs/invitees.json", "outputs/supplies.json"]}]),
            ("engines/commit/transform.py", "invalid_payload_type", [commit_payloads, {"name": "commit", "inputs": ["outputs/calendar.json", "outputs/invitees.json", "outputs/supplies.json"]}]),
        ]

        for target, rule, args in probes:
            with self.subTest(target=target, rule=rule):
                check_api_boundary(target, rule=rule, contract_path="README.md",
                                   requirement_quote="任意嵌套NaN/Infinity抛ValueError", args=args)


if __name__ == "__main__":
    unittest.main()
