import unittest

README = "README.md"

API_BOUNDARY_REQUIREMENTS = [
    {
        "target_path": "domains/calendar/transform.py",
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
                "requirement_quote": "仅对象/数组顶层合法；非法JSON、其他顶层类型和任意嵌套NaN/Infinity抛ValueError",
            },
        },
    },
    {
        "target_path": "domains/channels/transform.py",
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
                "requirement_quote": "仅对象/数组顶层合法；非法JSON、其他顶层类型和任意嵌套NaN/Infinity抛ValueError",
            },
        },
    },
    {
        "target_path": "views/notifications/transform.py",
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
                "requirement_quote": "仅对象/数组顶层合法；非法JSON、其他顶层类型和任意嵌套NaN/Infinity抛ValueError",
            },
        },
    },
]


def _calendar_payload():
    return {
        "events": [
            {
                "id": "e0",
                "start": 0,
                "end": 30,
                "social": True,
                "cancelled": False,
                "attendees": ["c0"],
            },
            {
                "id": "e1",
                "start": 1000,
                "end": 1030,
                "social": True,
                "cancelled": False,
                "attendees": ["c0"],
            },
        ],
        "day": 0,
        "contacts": [
            {"id": "c0", "email": "a@x", "message": "m0", "chat": None},
        ],
    }


def _channels_payload():
    return {
        "events": [],
        "day": 0,
        "contacts": [
            {"id": "c0", "email": "a@x", "message": "m0", "chat": None},
            {"id": "c1", "email": None, "message": None, "chat": "h1"},
            {"id": "c2", "email": None, "message": None, "chat": None},
        ],
    }


class CalendarBehaviorTests(unittest.TestCase):
    def test_cancel_morning_selects_morning_social_uncancelled(self):
        payload = _calendar_payload()
        contract = {"name": "calendar", "inputs": ["x"], "output": "y"}
        result = call_candidate(
            "domains/calendar/transform.py", "transform", args=[[payload], contract]
        )
        self.assertEqual(result["name"], "calendar")
        self.assertEqual(result["result"]["cancelled"], ["e0"])
        self.assertEqual(list(result["result"]["snapshots"]), ["e0"])
        self.assertEqual(list(result["result"]["remaining"]), ["e1"])

    def test_cancel_morning_rejects_end_not_after_start(self):
        payload = _calendar_payload()
        payload["events"][0]["end"] = payload["events"][0]["start"]
        contract = {"name": "calendar", "inputs": ["x"], "output": "y"}
        with self.assertRaises(CandidateCallError) as ctx:
            call_candidate(
                "domains/calendar/transform.py", "transform", args=[[payload], contract]
            )
        self.assertEqual(ctx.exception.details["failure_phase"], "candidate_exception")
        self.assertEqual(ctx.exception.details["error_type"], "ValueError")


class ChannelsBehaviorTests(unittest.TestCase):
    def test_channel_directory_prefers_message_then_chat(self):
        payload = _channels_payload()
        contract = {"name": "channels", "inputs": ["x"], "output": "y"}
        result = call_candidate(
            "domains/channels/transform.py", "transform", args=[[payload], contract]
        )
        contacts = result["result"]["contacts"]
        self.assertEqual(contacts["c0"]["primary"], "message")
        self.assertEqual(contacts["c0"]["address"], "m0")
        self.assertEqual(contacts["c1"]["primary"], "chat")
        self.assertEqual(contacts["c1"]["address"], "h1")
        self.assertIsNone(contacts["c2"]["primary"])
        self.assertIsNone(contacts["c2"]["address"])

    def test_channel_directory_rejects_duplicate_contact_id(self):
        payload = _channels_payload()
        payload["contacts"].append(
            {"id": "c0", "email": None, "message": None, "chat": None}
        )
        contract = {"name": "channels", "inputs": ["x"], "output": "y"}
        with self.assertRaises(CandidateCallError) as ctx:
            call_candidate(
                "domains/channels/transform.py", "transform", args=[[payload], contract]
            )
        self.assertEqual(ctx.exception.details["failure_phase"], "candidate_exception")
        self.assertEqual(ctx.exception.details["error_type"], "ValueError")


class NotificationsBehaviorTests(unittest.TestCase):
    def test_cancel_notifications_routes_email_message_chat_unreachable(self):
        cancel = {
            "cancelled": ["e0"],
            "snapshots": {"e0": {"id": "e0", "attendees": ["c0", "c1", "c2", "c3"]}},
            "remaining": {},
        }
        channels = {
            "contacts": {
                "c0": {"email": "a@x", "primary": "message", "address": "m0"},
                "c1": {"email": None, "primary": "chat", "address": "h1"},
                "c2": {"email": "b@x", "primary": None, "address": None},
                "c3": {"email": None, "primary": None, "address": None},
            }
        }
        contract = {"name": "notifications", "inputs": ["a", "b"], "output": "y"}
        result = call_candidate(
            "views/notifications/transform.py",
            "transform",
            args=[[cancel, channels], contract],
        )
        r = result["result"]
        self.assertEqual(r["unreachable"], ["c3"])
        self.assertEqual(r["group"]["id"], "cancelled-social")
        self.assertEqual(r["group"]["members"], ["c0"])
        self.assertEqual(r["group"]["requires"], ["e0"])
        channels_seen = sorted(o["channel"] for o in r["outbox"])
        self.assertEqual(channels_seen, ["chat", "email", "email", "message_group"])

    def test_cancel_notifications_rejects_unknown_attendee(self):
        cancel = {
            "cancelled": ["e0"],
            "snapshots": {"e0": {"id": "e0", "attendees": ["cX"]}},
            "remaining": {},
        }
        channels = {"contacts": {}}
        contract = {"name": "notifications", "inputs": ["a", "b"], "output": "y"}
        with self.assertRaises(CandidateCallError) as ctx:
            call_candidate(
                "views/notifications/transform.py",
                "transform",
                args=[[cancel, channels], contract],
            )
        self.assertEqual(ctx.exception.details["failure_phase"], "candidate_exception")
        self.assertEqual(ctx.exception.details["error_type"], "ValueError")


class ApiBoundaryTests(unittest.TestCase):
    def test_nonfinite_unknown_field_rejected(self):
        for target in (
            "domains/calendar/transform.py",
            "domains/channels/transform.py",
            "views/notifications/transform.py",
        ):
            with self.subTest(target=target):
                if target == "domains/calendar/transform.py":
                    args = [[_calendar_payload()], {"name": "c", "inputs": ["x"], "output": "y"}]
                elif target == "domains/channels/transform.py":
                    args = [[_channels_payload()], {"name": "c", "inputs": ["x"], "output": "y"}]
                else:
                    args = [
                        [
                            {"cancelled": [], "snapshots": {}, "remaining": {}},
                            {"contacts": {}},
                        ],
                        {"name": "n", "inputs": ["a", "b"], "output": "y"},
                    ]
                check_api_boundary(
                    target,
                    rule="nonfinite_unknown_field",
                    contract_path=README,
                    requirement_quote="未知额外字段可忽略，但其中非有限JSON仍非法",
                    args=args,
                )

    def test_invalid_payload_type_rejected(self):
        for target in (
            "domains/calendar/transform.py",
            "domains/channels/transform.py",
            "views/notifications/transform.py",
        ):
            with self.subTest(target=target):
                if target == "domains/calendar/transform.py":
                    args = [[_calendar_payload()], {"name": "c", "inputs": ["x"], "output": "y"}]
                elif target == "domains/channels/transform.py":
                    args = [[_channels_payload()], {"name": "c", "inputs": ["x"], "output": "y"}]
                else:
                    args = [
                        [
                            {"cancelled": [], "snapshots": {}, "remaining": {}},
                            {"contacts": {}},
                        ],
                        {"name": "n", "inputs": ["a", "b"], "output": "y"},
                    ]
                check_api_boundary(
                    target,
                    rule="invalid_payload_type",
                    contract_path=README,
                    requirement_quote="仅对象/数组顶层合法；非法JSON、其他顶层类型和任意嵌套NaN/Infinity抛ValueError",
                    args=args,
                )


if __name__ == "__main__":
    unittest.main()
