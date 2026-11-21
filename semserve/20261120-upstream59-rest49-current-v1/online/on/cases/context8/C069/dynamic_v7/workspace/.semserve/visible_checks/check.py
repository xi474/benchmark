import base64
import json
import unittest


def _decode_ssh(cert):
    payload_b64 = cert[len("SSH-MODEL1."):]
    pad = "=" * (-len(payload_b64) % 4)
    return json.loads(base64.urlsafe_b64decode(payload_b64 + pad).decode("utf-8"))


class TestTransformBehavior(unittest.TestCase):
    def test_initial_session_and_simple_renew(self):
        payload = {
            "user": {"name": "alice", "roles": ["base"],
                     "traits": {"logins": ["alice"], "db_users": ["db1"]}},
            "start_time": 0,
            "session_ttl": 100,
            "access_requests": {},
            "events": [{"op": "renew", "id": "s1", "time": 10, "prev": "s0"}],
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(result["session_ids"], ["s0", "s1"])
        self.assertEqual(result["replies"][0]["status"], "ok")
        self.assertEqual(result["replies"][0]["id"], "s1")

    def test_expired_prev(self):
        payload = {
            "user": {"name": "a", "roles": [], "traits": {"logins": [], "db_users": []}},
            "start_time": 0,
            "session_ttl": 10,
            "access_requests": {},
            "events": [{"op": "renew", "id": "s1", "time": 10, "prev": "s0"}],
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(result["replies"][0]["status"], "expired")
        self.assertEqual(result["session_ids"], ["s0"])

    def test_request_unavailable_not_approved(self):
        payload = {
            "user": {"name": "a", "roles": [], "traits": {"logins": [], "db_users": []}},
            "start_time": 0,
            "session_ttl": 100,
            "access_requests": {"r1": {"approved": False, "expiry": 50, "roles": ["x"]}},
            "events": [{"op": "renew", "id": "s1", "time": 10, "prev": "s0",
                        "access_request": "r1"}],
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(result["replies"][0]["status"], "request_unavailable")
        self.assertEqual(result["session_ids"], ["s0"])

    def test_resource_already_active(self):
        payload = {
            "user": {"name": "a", "roles": [], "traits": {"logins": [], "db_users": []}},
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
        self.assertEqual(result["replies"][1]["status"], "resource_already_active")
        self.assertEqual(result["session_ids"], ["s0", "s1"])

    def test_role_accumulation_and_switchback(self):
        payload = {
            "user": {"name": "a", "roles": ["base"],
                     "traits": {"logins": [], "db_users": []}},
            "start_time": 0,
            "session_ttl": 100,
            "access_requests": {
                "r1": {"approved": True, "expiry": 50, "roles": ["reader"]},
                "r2": {"approved": True, "expiry": 60, "roles": ["writer"]},
            },
            "events": [
                {"op": "renew", "id": "s1", "time": 10, "prev": "s0", "access_request": "r1"},
                {"op": "renew", "id": "s2", "time": 20, "prev": "s1", "access_request": "r2"},
                {"op": "renew", "id": "s3", "time": 30, "prev": "s2", "switchback": True},
            ],
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(result["replies"][0]["status"], "ok")
        self.assertEqual(result["replies"][1]["status"], "ok")
        self.assertEqual(result["replies"][2]["status"], "ok")
        obj = _decode_ssh(result["replies"][2]["ssh_certificate"])
        self.assertEqual(obj["roles"], ["base"])
        self.assertEqual(obj["allowed_resources"], [])

    def test_update_user_and_reload(self):
        payload = {
            "user": {"name": "a", "roles": ["base"],
                     "traits": {"logins": [], "db_users": []}},
            "start_time": 0,
            "session_ttl": 100,
            "access_requests": {},
            "events": [
                {"op": "update_user", "time": 5, "roles": ["admin"]},
                {"op": "renew", "id": "s1", "time": 10, "prev": "s0", "reload_user": True},
            ],
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(result["replies"][0]["status"], "ok")
        obj = _decode_ssh(result["replies"][0]["ssh_certificate"])
        self.assertEqual(obj["roles"], ["admin"])

    def test_input_not_mutated(self):
        payload = {
            "user": {"name": "a", "roles": ["base"],
                     "traits": {"logins": ["a"], "db_users": ["db"]}},
            "start_time": 0,
            "session_ttl": 100,
            "access_requests": {"r1": {"approved": True, "expiry": 50, "roles": ["x"]}},
            "events": [{"op": "renew", "id": "s1", "time": 10, "prev": "s0",
                        "access_request": "r1"}],
        }
        snapshot = json.loads(json.dumps(payload))
        call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(payload, snapshot)


if __name__ == "__main__":
    unittest.main()
