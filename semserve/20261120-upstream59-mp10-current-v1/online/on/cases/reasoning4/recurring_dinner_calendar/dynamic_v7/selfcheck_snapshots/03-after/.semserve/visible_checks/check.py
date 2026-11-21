import unittest

# Injected by the visible-contract SDK runner. These names are available in the
# test process without import.
try:
    call_candidate  # noqa: F401
    CandidateCallError  # noqa: F401
    check_api_boundary  # noqa: F401
except NameError:
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


# Finite seeds matching each transform's public signature.
def _dates_seed():
    return [{"today": "2026-11-04", "events": [], "contacts": []},
            {"name": "dates", "operation": "dinner_days",
             "inputs": ["inputs/case.json"], "output": "outputs/dates.json"}]


def _calendar_seed():
    return [{"today": "2026-11-04", "contacts": ["a"],
             "events": [{"id": "e1", "start": "2026-11-04T18:00",
                         "end": "2026-11-04T19:00", "kind": "other",
                         "attendees": ["a"]}]},
            {"name": "calendar", "operation": "dinner_calendar_index",
             "inputs": ["inputs/case.json"], "output": "outputs/calendar.json"}]


def _plan_seed():
    return [{"dates": ["2026-11-04"]},
            {"events": [], "existing_dinners": []},
            {"name": "plan", "operation": "dinner_change_plan",
             "inputs": ["outputs/dates.json", "outputs/calendar.json"],
             "output": "outputs/plan.json"}]


def _notifications_seed():
    return [{"snapshots": []},
            {"name": "notifications", "operation": "dinner_notifications",
             "inputs": ["outputs/plan.json"], "output": "outputs/notifications.json"}]


def _apply_seed():
    return [{"events": []},
            {"cancelled": [], "added": []},
            {"outbox": []},
            {"name": "apply", "operation": "dinner_apply",
             "inputs": ["outputs/calendar.json", "outputs/plan.json",
                        "outputs/notifications.json"],
             "output": "outputs/apply.json"}]


SEEDS = {
    "engines/dates/transform.py": _dates_seed,
    "engines/calendar/transform.py": _calendar_seed,
    "engines/plan/transform.py": _plan_seed,
    "engines/notifications/transform.py": _notifications_seed,
    "engines/apply/transform.py": _apply_seed,
}


class TestDates(unittest.TestCase):
    def test_dates_range(self):
        # today=2026-11-04 (Wednesday) -> next natural week Friday 2026-11-13.
        result = call_candidate("engines/dates/transform.py", "transform",
                                args=_dates_seed())
        self.assertEqual(result["name"], "dates")
        self.assertEqual(result["result"]["dates"][0], "2026-11-04")
        self.assertEqual(result["result"]["dates"][-1], "2026-11-13")
        self.assertEqual(len(result["result"]["dates"]), 10)

    def test_dates_monday_start(self):
        # today=2026-11-09 (Monday) -> next natural week Friday 2026-11-20.
        seed = _dates_seed()
        seed[0]["today"] = "2026-11-09"
        result = call_candidate("engines/dates/transform.py", "transform",
                                args=seed)
        self.assertEqual(result["result"]["dates"],
                         ["2026-11-09", "2026-11-10", "2026-11-11",
                          "2026-11-12", "2026-11-13", "2026-11-14",
                          "2026-11-15", "2026-11-16", "2026-11-17",
                          "2026-11-18", "2026-11-19", "2026-11-20"])


class TestCalendar(unittest.TestCase):
    def test_existing_dinner_dedup(self):
        seed = _calendar_seed()
        seed[0]["events"] = [
            {"id": "d1", "start": "2026-11-05T19:00", "end": "2026-11-05T19:10",
             "kind": "dinner", "attendees": ["a"]},
            {"id": "d2", "start": "2026-11-05T19:00", "end": "2026-11-05T19:05",
             "kind": "dinner", "attendees": ["a"]},
        ]
        result = call_candidate("engines/calendar/transform.py", "transform",
                                args=seed)
        self.assertEqual(result["result"]["existing_dinners"], ["2026-11-05"])

    def test_attendees_dedup_sorted(self):
        seed = _calendar_seed()
        seed[0]["contacts"] = ["a", "b"]
        seed[0]["events"] = [
            {"id": "e1", "start": "2026-11-04T18:00", "end": "2026-11-04T19:00",
             "kind": "other", "attendees": ["b", "a", "a"]},
        ]
        result = call_candidate("engines/calendar/transform.py", "transform",
                                args=seed)
        self.assertEqual(result["result"]["events"][0]["attendees"], ["a", "b"])


class TestPlan(unittest.TestCase):
    def test_plan_skip_existing_and_cancel(self):
        seed = _plan_seed()
        seed[0] = {"dates": ["2026-11-04", "2026-11-05"]}
        seed[1] = {
            "events": [
                {"id": "old", "start": "2026-11-04T19:30", "end": "2026-11-04T20:30",
                 "kind": "other", "attendees": ["a"]},
            ],
            "existing_dinners": ["2026-11-05"],
        }
        result = call_candidate("engines/plan/transform.py", "transform",
                                args=seed)
        added_ids = [e["id"] for e in result["result"]["added"]]
        self.assertEqual(added_ids, ["dinner-2026-11-04"])
        self.assertEqual(result["result"]["cancelled"], ["old"])

    def test_plan_exact_end_no_conflict(self):
        seed = _plan_seed()
        seed[0] = {"dates": ["2026-11-04"]}
        seed[1] = {
            "events": [
                {"id": "edge", "start": "2026-11-04T18:00", "end": "2026-11-04T19:00",
                 "kind": "other", "attendees": ["a"]},
            ],
            "existing_dinners": [],
        }
        result = call_candidate("engines/plan/transform.py", "transform",
                                args=seed)
        self.assertEqual(result["result"]["cancelled"], [])


class TestNotifications(unittest.TestCase):
    def test_outbox_grouped(self):
        seed = _notifications_seed()
        seed[0] = {
            "snapshots": [
                {"id": "x", "attendees": ["b", "a"]},
                {"id": "y", "attendees": ["a"]},
            ],
        }
        result = call_candidate("engines/notifications/transform.py", "transform",
                                args=seed)
        outbox = result["result"]["outbox"]
        self.assertEqual([o["to"] for o in outbox], ["a", "b"])
        self.assertEqual(outbox[0]["event_ids"], ["x", "y"])
        self.assertEqual(outbox[1]["event_ids"], ["x"])


class TestApply(unittest.TestCase):
    def test_apply_remove_and_add(self):
        seed = _apply_seed()
        seed[0] = {"events": [
            {"id": "old", "start": "2026-11-04T19:30", "end": "2026-11-04T20:30",
             "kind": "other", "attendees": ["a"]},
            {"id": "keep", "start": "2026-11-05T18:00", "end": "2026-11-05T19:00",
             "kind": "other", "attendees": ["a"]},
        ]}
        seed[1] = {
            "cancelled": ["old"],
            "added": [{"id": "dinner-2026-11-04", "start": "2026-11-04T19:00",
                       "end": "2026-11-04T20:00", "kind": "dinner", "attendees": []}],
        }
        seed[2] = {"outbox": [{"to": "a", "event_ids": ["old"]}]}
        result = call_candidate("engines/apply/transform.py", "transform",
                                args=seed)
        ids = [e["id"] for e in result["result"]["events"]]
        self.assertEqual(ids, ["dinner-2026-11-04", "keep"])
        self.assertEqual(result["result"]["outbox"], seed[2]["outbox"])


class TestApiBoundaries(unittest.TestCase):
    def test_api_boundary_rules(self):
        for spec in API_BOUNDARY_REQUIREMENTS:
            for rule, cfg in spec["rules"].items():
                with self.subTest(target=spec["target_path"], rule=rule):
                    if not cfg["applicable"]:
                        continue
                    seed = SEEDS[spec["target_path"]]()
                    check_api_boundary(
                        spec["target_path"], rule=rule,
                        contract_path=cfg["contract_path"],
                        requirement_quote=cfg["requirement_quote"],
                        args=seed)


if __name__ == "__main__":
    unittest.main()
