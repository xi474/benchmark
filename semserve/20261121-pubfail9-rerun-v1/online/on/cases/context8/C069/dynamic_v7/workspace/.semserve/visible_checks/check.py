import unittest

API_BOUNDARY_REQUIREMENTS = [
    {
        "target_path": "solution.py",
        "function": "transform",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": False,
                "contract_path": "TASK.md",
                "requirement_quote": "不要求额外NaN/Infinity防御",
                "reason": "Public contract explicitly excludes NaN/Infinity defense.",
            },
            "invalid_payload_type": {
                "applicable": False,
                "contract_path": "TASK.md",
                "requirement_quote": "不要求额外NaN/Infinity防御",
                "reason": "Public contract does not require ValueError on invalid payload types.",
            },
        },
    },
]


class TestSessionRenewal(unittest.TestCase):
    def test_renew_roles_resources_union_and_encoding(self):
        payload = {
            "user": {"name": "bob", "roles": ["base"], "traits": {"logins": ["bob"], "db_users": ["db"]}},
            "start_time": 0,
            "session_ttl": 100,
            "access_requests": {
                "r1": {"approved": True, "expiry": 70, "roles": ["reader"]},
                "q1": {"approved": True, "expiry": 50, "resources": ["db:one"]},
            },
            "events": [
                {"op": "renew", "id": "s1", "time": 10, "prev": "s0", "access_request": "r1"},
                {"op": "renew", "id": "s2", "time": 20, "prev": "s1", "access_request": "q1"},
            ],
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(result["session_ids"], ["s0", "s1", "s2"])
        self.assertEqual(len(result["replies"]), 2)
        self.assertEqual(result["replies"][0]["status"], "ok")
        self.assertEqual(result["replies"][1]["status"], "ok")

    def test_expired_prev_fails(self):
        payload = {
            "user": {"name": "bob", "roles": ["base"], "traits": {"logins": ["bob"], "db_users": ["db"]}},
            "start_time": 0,
            "session_ttl": 10,
            "access_requests": {},
            "events": [
                {"op": "renew", "id": "s1", "time": 20, "prev": "s0"},
            ],
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(result["session_ids"], ["s0"])
        self.assertEqual(result["replies"], [{"id": "s1", "status": "expired"}])

    def test_resource_already_active(self):
        payload = {
            "user": {"name": "bob", "roles": ["base"], "traits": {"logins": ["bob"], "db_users": ["db"]}},
            "start_time": 0,
            "session_ttl": 100,
            "access_requests": {
                "q1": {"approved": True, "expiry": 50, "resources": ["db:one"]},
                "q2": {"approved": True, "expiry": 60, "resources": ["db:two"]},
            },
            "events": [
                {"op": "renew", "id": "s1", "time": 10, "prev": "s0", "access_request": "q1"},
                {"op": "renew", "id": "s2", "time": 20, "prev": "s1", "access_request": "q2"},
            ],
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(result["replies"][1], {"id": "s2", "status": "resource_already_active"})
        self.assertEqual(result["session_ids"], ["s0", "s1"])

    def test_request_unavailable_when_expired(self):
        payload = {
            "user": {"name": "bob", "roles": ["base"], "traits": {"logins": ["bob"], "db_users": ["db"]}},
            "start_time": 0,
            "session_ttl": 100,
            "access_requests": {
                "r1": {"approved": True, "expiry": 15, "roles": ["reader"]},
            },
            "events": [
                {"op": "renew", "id": "s1", "time": 20, "prev": "s0", "access_request": "r1"},
            ],
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(result["replies"], [{"id": "s1", "status": "request_unavailable"}])
        self.assertEqual(result["session_ids"], ["s0"])

    def test_switchback_clears_requests(self):
        payload = {
            "user": {"name": "bob", "roles": ["base"], "traits": {"logins": ["bob"], "db_users": ["db"]}},
            "start_time": 0,
            "session_ttl": 100,
            "access_requests": {
                "r1": {"approved": True, "expiry": 70, "roles": ["reader"]},
            },
            "events": [
                {"op": "renew", "id": "s1", "time": 10, "prev": "s0", "access_request": "r1"},
                {"op": "renew", "id": "s2", "time": 20, "prev": "s1", "switchback": True},
            ],
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(result["replies"][1]["status"], "ok")
        import base64
        import json
        cert = result["replies"][1]["ssh_certificate"]
        body = cert[len("SSH-MODEL1."):]
        pad = "=" * (-len(body) % 4)
        decoded = json.loads(base64.urlsafe_b64decode(body + pad).decode("utf-8"))
        self.assertEqual(decoded["roles"], ["base"])
        self.assertEqual(decoded["allowed_resources"], [])

    def test_update_user_reload(self):
        payload = {
            "user": {"name": "bob", "roles": ["base"], "traits": {"logins": ["bob"], "db_users": ["db"]}},
            "start_time": 0,
            "session_ttl": 100,
            "access_requests": {},
            "events": [
                {"op": "update_user", "time": 5, "roles": ["admin"]},
                {"op": "renew", "id": "s1", "time": 10, "prev": "s0", "reload_user": True},
            ],
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        import base64
        import json
        cert = result["replies"][0]["ssh_certificate"]
        body = cert[len("SSH-MODEL1."):]
        pad = "=" * (-len(body) % 4)
        decoded = json.loads(base64.urlsafe_b64decode(body + pad).decode("utf-8"))
        self.assertEqual(decoded["roles"], ["admin"])


if __name__ == "__main__":
    unittest.main()
