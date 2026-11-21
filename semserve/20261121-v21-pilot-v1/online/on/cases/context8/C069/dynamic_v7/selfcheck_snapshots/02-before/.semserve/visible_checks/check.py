import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PUBLIC_INPUT = json.loads((ROOT / "public_input.json").read_text(encoding="utf-8"))
PUBLIC_EXPECTED = json.loads((ROOT / "public_expected.json").read_text(encoding="utf-8"))

# Visible document for API boundary classification.
visible_document = str(ROOT / "TASK.md")

API_BOUNDARY_REQUIREMENTS = [
    {
        "target_path": "solution.py",
        "function": "transform",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": False,
                "contract_path": visible_document,
                "requirement_quote": "不要求额外NaN/Infinity防御",
                "reason": "The public contract explicitly does not require NaN/Infinity defense.",
            },
            "invalid_payload_type": {
                "applicable": False,
                "contract_path": visible_document,
                "requirement_quote": "核心接口transform(payload)返回下述JSON结果",
                "reason": "The contract does not specify ValueError for a non-object payload.",
            },
        },
    },
]


class TestTransformContract(unittest.TestCase):
    def test_public_fixture_matches_expected(self):
        # Output contract: transform must reproduce the public expected result.
        result = call_candidate("solution.py", "transform", args=[PUBLIC_INPUT])
        self.assertEqual(result, PUBLIC_EXPECTED)

    def test_does_not_mutate_input(self):
        # State change: transform must not modify the input object.
        payload = json.loads(json.dumps(PUBLIC_INPUT))
        snapshot = json.loads(json.dumps(payload))
        call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(payload, snapshot)

    def test_initial_session_and_simple_renew(self):
        # Valid rare path: a single renew with no requests yields ok and s0/s1.
        payload = json.loads(json.dumps(PUBLIC_INPUT))
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(result["session_ids"], ["s0", "s1"])
        self.assertEqual(result["replies"][0]["status"], "ok")
        self.assertEqual(result["replies"][0]["id"], "s1")

    def test_expired_prev_yields_expired(self):
        # Failure path: renewing after prev expiry yields expired and no new session.
        payload = json.loads(json.dumps(PUBLIC_INPUT))
        payload["events"] = [
            {"op": "renew", "id": "s1", "time": 200, "prev": "s0"}
        ]
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(result["session_ids"], ["s0"])
        self.assertEqual(result["replies"], [{"id": "s1", "status": "expired"}])

    def test_role_request_accumulates_and_sorts(self):
        # Role union: base + reader + writer, sorted; expiry = min(now+ttl, req expiry).
        payload = json.loads(json.dumps(PUBLIC_INPUT))
        payload["events"] = [
            {"op": "renew", "id": "s1", "time": 10, "prev": "s0", "access_request": "r1"},
            {"op": "renew", "id": "s2", "time": 20, "prev": "s1", "access_request": "r2"},
        ]
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(result["session_ids"], ["s0", "s1", "s2"])
        self.assertEqual(result["replies"][1]["status"], "ok")
        import base64
        cert = result["replies"][1]["ssh_certificate"]
        body = cert.split(".", 1)[1]
        pad = "=" * (-len(body) % 4)
        obj = json.loads(base64.urlsafe_b64decode(body + pad).decode("utf-8"))
        self.assertEqual(obj["roles"], ["base", "reader", "writer"])
        self.assertEqual(obj["expires"], 60)

    def test_resource_already_active(self):
        # Resource request conflict: second resource request is rejected.
        payload = json.loads(json.dumps(PUBLIC_INPUT))
        payload["events"] = [
            {"op": "renew", "id": "s1", "time": 10, "prev": "s0", "access_request": "q1"},
            {"op": "renew", "id": "s2", "time": 20, "prev": "s1", "access_request": "q2"},
        ]
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(result["session_ids"], ["s0", "s1"])
        self.assertEqual(result["replies"][1], {"id": "s2", "status": "resource_already_active"})

    def test_request_unavailable_when_expired(self):
        # Expired request at assume time yields request_unavailable.
        payload = json.loads(json.dumps(PUBLIC_INPUT))
        payload["events"] = [
            {"op": "renew", "id": "s1", "time": 20, "prev": "s0", "access_request": "old"}
        ]
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(result["session_ids"], ["s0"])
        self.assertEqual(result["replies"], [{"id": "s1", "status": "request_unavailable"}])


if __name__ == "__main__":
    unittest.main()
