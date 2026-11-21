import unittest

# Injected by the visible-contract SDK runner. These names are available in the
# test process without import.
try:
    call_candidate  # noqa: F401
    CandidateCallError  # noqa: F401
    check_api_boundary  # noqa: F401
except NameError:
    # Fallback for a plain local run so the file still imports.
    def call_candidate(*a, **k):
        raise RuntimeError("call_candidate not injected")
    class CandidateCallError(Exception):
        pass
    def check_api_boundary(*a, **k):
        raise RuntimeError("check_api_boundary not injected")


README = "README.md"

# Every transform API documented by the README. Both rules are reviewed per API.
API_BOUNDARY_REQUIREMENTS = [
    {
        "target_path": "engines/dates/transform.py",
        "function": "transform",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": True,
                "contract_path": README,
                "requirement_quote": "未知额外字段可忽略，但其中非有限JSON仍非法",
            },
            "invalid_payload_type": {
                "applicable": True,
                "contract_path": README,
                "requirement_quote": "model.load_payload(path:Path)：读取UTF8 JSON，仅对象/数组顶层合法",
            },
        },
    },
    {
        "target_path": "engines/calendar/transform.py",
        "function": "transform",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": True,
                "contract_path": README,
                "requirement_quote": "未知额外字段可忽略，但其中非有限JSON仍非法",
            },
            "invalid_payload_type": {
                "applicable": True,
                "contract_path": README,
                "requirement_quote": "model.load_payload(path:Path)：读取UTF8 JSON，仅对象/数组顶层合法",
            },
        },
    },
    {
        "target_path": "engines/plan/transform.py",
        "function": "transform",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": True,
                "contract_path": README,
                "requirement_quote": "未知额外字段可忽略，但其中非有限JSON仍非法",
            },
            "invalid_payload_type": {
                "applicable": True,
                "contract_path": README,
                "requirement_quote": "model.load_payload(path:Path)：读取UTF8 JSON，仅对象/数组顶层合法",
            },
        },
    },
    {
        "target_path": "engines/notifications/transform.py",
        "function": "transform",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": True,
                "contract_path": README,
                "requirement_quote": "未知额外字段可忽略，但其中非有限JSON仍非法",
            },
            "invalid_payload_type": {
                "applicable": True,
                "contract_path": README,
                "requirement_quote": "model.load_payload(path:Path)：读取UTF8 JSON，仅对象/数组顶层合法",
            },
        },
    },
    {
        "target_path": "engines/apply/transform.py",
        "function": "transform",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": True,
                "contract_path": README,
                "requirement_quote": "未知额外字段可忽略，但其中非有限JSON仍非法",
            },
            "invalid_payload_type": {
                "applicable": True,
                "contract_path": README,
                "requirement_quote": "model.load_payload(path:Path)：读取UTF8 JSON，仅对象/数组顶层合法",
            },
        },
    },
]


class TestDates(unittest.TestCase):
    def test_dates_range(self):
        # today=2026-11-04 (Wednesday) -> next natural week Friday 2026-11-13.
        payload = {"today": "2026-11-04", "events": [], "contacts": []}
        contract = {"name": "dates", "operation": "dinner_days",
                    "inputs": ["inputs/case.json"], "output": "outputs/dates.json"}
        result = call_candidate("engines/dates/transform.py", "transform",
                                args=[[payload], contract])
        self.assertEqual(result["name"], "dates")
        self.assertEqual(result["result"]["dates"][0], "2026-11-04")
        self.assertEqual(result["result"]["dates"][-1], "2026-11-13")
        self.assertEqual(len(result["result"]["dates"]), 10)

    def test_dates_monday_start(self):
        # today=2026-11-09 (Monday) -> Friday 2026-11-13.
        payload = {"today": "2026-11-09", "events": [], "contacts": []}
        contract = {"name": "dates", "operation": "dinner_days",
                    "inputs": ["inputs/case.json"], "output": "outputs/dates.json"}
        result = call_candidate("engines/dates/transform.py", "transform",
                                args=[[payload], contract])
        self.assertEqual(result["result"]["dates"],
                         ["2026-11-09", "2026-11-10", "2026-11-11",
                          "2026-11-12", "2026-11-13"])


class TestCalendar(unittest.TestCase):
    def test_existing_dinner_dedup(self):
        payload = {
            "today": "2026-11-04",
            "contacts": ["a"],
            "events": [
                {"id": "d1", "start": "2026-11-05T19:00", "end": "2026-11-05T19:10",
                 "kind": "dinner", "attendees": ["a"]},
                {"id": "d2", "start": "2026-11-05T19:00", "end": "2026-11-05T19:05",
                 "kind": "dinner", "attendees": ["a"]},
            ],
        }
        contract = {"name": "calendar", "operation": "dinner_calendar_index",
                    "inputs": ["inputs/case.json"], "output": "outputs/calendar.json"}
        result = call_candidate("engines/calendar/transform.py", "transform",
                                args=[[payload], contract])
        self.assertEqual(result["result"]["existing_dinners"], ["2026-11-05"])

    def test_attendees_dedup_sorted(self):
        payload = {
            "today": "2026-11-04",
            "contacts": ["a", "b"],
            "events": [
                {"id": "e1", "start": "2026-11-04T18:00", "end": "2026-11-04T19:00",
                 "kind": "other", "attendees": ["b", "a", "a"]},
            ],
        }
        contract = {"name": "calendar", "operation": "dinner_calendar_index",
                    "inputs": ["inputs/case.json"], "output": "outputs/calendar.json"}
        result = call_candidate("engines/calendar/transform.py", "transform",
                                args=[[payload], contract])
        self.assertEqual(result["result"]["events"][0]["attendees"], ["a", "b"])


class TestPlan(unittest.TestCase):
    def test_plan_skip_existing_and_cancel(self):
        days = {"dates": ["2026-11-04", "2026-11-05"]}
        calendar = {
            "events": [
                {"id": "old", "start": "2026-11-04T19:30", "end": "2026-11-04T20:30",
                 "kind": "other", "attendees": ["a"]},
            ],
            "existing_dinners": ["2026-11-05"],
        }
        contract = {"name": "plan", "operation": "dinner_change_plan",
                    "inputs": ["outputs/dates.json", "outputs/calendar.json"],
                    "output": "outputs/plan.json"}
        result = call_candidate("engines/plan/transform.py", "transform",
                                args=[[days, calendar], contract])
        added_ids = [e["id"] for e in result["result"]["added"]]
        self.assertEqual(added_ids, ["dinner-2026-11-04"])
        self.assertEqual(result["result"]["cancelled"], ["old"])

    def test_plan_exact_end_no_conflict(self):
        days = {"dates": ["2026-11-04"]}
        calendar = {
            "events": [
                {"id": "edge", "start": "2026-11-04T18:00", "end": "2026-11-04T19:00",
                 "kind": "other", "attendees": ["a"]},
            ],
            "existing_dinners": [],
        }
        contract = {"name": "plan", "operation": "dinner_change_plan",
                    "inputs": ["outputs/dates.json", "outputs/calendar.json"],
                    "output": "outputs/plan.json"}
        result = call_candidate("engines/plan/transform.py", "transform",
                                args=[[days, calendar], contract])
        self.assertEqual(result["result"]["cancelled"], [])


class TestNotifications(unittest.TestCase):
    def test_outbox_grouped(self):
        plan = {
            "snapshots": [
                {"id": "x", "attendees": ["b", "a"]},
                {"id": "y", "attendees": ["a"]},
            ],
        }
        contract = {"name": "notifications", "operation": "dinner_notifications",
                    "inputs": ["outputs/plan.json"], "output": "outputs/notifications.json"}
        result = call_candidate("engines/notifications/transform.py", "transform",
                                args=[[plan], contract])
        outbox = result["result"]["outbox"]
        self.assertEqual([o["to"] for o in outbox], ["a", "b"])
        self.assertEqual(outbox[0]["event_ids"], ["x", "y"])
        self.assertEqual(outbox[1]["event_ids"], ["x"])


class TestApply(unittest.TestCase):
    def test_apply_remove_and_add(self):
        calendar = {"events": [
            {"id": "old", "start": "2026-11-04T19:30", "end": "2026-11-04T20:30",
             "kind": "other", "attendees": ["a"]},
            {"id": "keep", "start": "2026-11-05T18:00", "end": "2026-11-05T19:00",
             "kind": "other", "attendees": ["a"]},
        ]}
        plan = {
            "cancelled": ["old"],
            "added": [{"id": "dinner-2026-11-04", "start": "2026-11-04T19:00",
                       "end": "2026-11-04T20:00", "kind": "dinner", "attendees": []}],
        }
        notifications = {"outbox": [{"to": "a", "event_ids": ["old"]}]}
        contract = {"name": "apply", "operation": "dinner_apply",
                    "inputs": ["outputs/calendar.json", "outputs/plan.json",
                               "outputs/notifications.json"],
                    "output": "outputs/apply.json"}
        result = call_candidate("engines/apply/transform.py", "transform",
                                args=[[calendar, plan, notifications], contract])
        ids = [e["id"] for e in result["result"]["events"]]
        self.assertEqual(ids, ["dinner-2026-11-04", "keep"])
        self.assertEqual(result["result"]["outbox"], notifications["outbox"])


class TestApiBoundaries(unittest.TestCase):
    def test_api_boundary_rules(self):
        for spec in API_BOUNDARY_REQUIREMENTS:
            for rule, cfg in spec["rules"].items():
                with self.subTest(target=spec["target_path"], rule=rule):
                    if not cfg["applicable"]:
                        continue
                    if rule == "nonfinite_unknown_field":
                        check_api_boundary(
                            spec["target_path"], rule=rule,
                            contract_path=cfg["contract_path"],
                            requirement_quote=cfg["requirement_quote"],
                            args=[[{"today": "2026-11-04", "events": [],
                                    "contacts": []},
                                   {"name": "dates", "operation": "dinner_days",
                                    "inputs": ["inputs/case.json"],
                                    "output": "outputs/dates.json"}]])
                    elif rule == "invalid_payload_type":
                        check_api_boundary(
                            spec["target_path"], rule=rule,
                            contract_path=cfg["contract_path"],
                            requirement_quote=cfg["requirement_quote"],
                            args=[[{"today": "2026-11-04", "events": [],
                                    "contacts": []},
                                   {"name": "dates", "operation": "dinner_days",
                                    "inputs": ["inputs/case.json"],
                                    "output": "outputs/dates.json"}]])
                    else:
                        raise AssertionError("unhandled rule %s" % rule)


if __name__ == "__main__":
    unittest.main()
