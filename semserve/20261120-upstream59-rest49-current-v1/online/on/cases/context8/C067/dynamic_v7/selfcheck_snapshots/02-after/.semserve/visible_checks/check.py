import unittest

API_BOUNDARY_REQUIREMENTS = [
    {
        "target_path": "solution.py",
        "function": "transform",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": False,
                "contract_path": "TASK.md",
                "requirement_quote": "验收覆盖本文正常输入域与完整交付，不要求额外NaN/Infinity防御",
                "reason": "Public spec explicitly excludes NaN/Infinity defense.",
            },
            "invalid_payload_type": {
                "applicable": False,
                "contract_path": "TASK.md",
                "requirement_quote": "核心接口transform(payload)返回下述JSON结果",
                "reason": "Spec does not require ValueError on invalid payload type.",
            },
        },
    },
]


class TestTransform(unittest.TestCase):
    def test_denied_request_no_service_lookup(self):
        # A request not allowed must be denied without service lookup or cert.
        payload = {
            "ttl": 5,
            "clusters": {"away": {"mode": "remote", "services": {"k": True}}},
            "policies": {"bob": [{"cluster": "away", "verb": "read"}]},
            "events": [
                {"op": "request", "id": "x", "time": 0, "user": "alice",
                 "cluster": "away", "service": "k", "verb": "read"}
            ],
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(result["replies"], [{"id": "x", "status": "denied"}])
        self.assertEqual(result["authorizer_calls"], 1)
        self.assertEqual(result["service_lookups"], 0)
        self.assertEqual(result["remote_routes"], 0)
        self.assertEqual(result["certificates_issued"], 0)
        self.assertEqual(result["cache"], [])

    def test_not_found_after_allow(self):
        # Allowed but service unavailable -> not_found, no cert, no route.
        payload = {
            "ttl": 5,
            "clusters": {"away": {"mode": "remote", "services": {"k": False}}},
            "policies": {"alice": [{"cluster": "away", "verb": "read"}]},
            "events": [
                {"op": "request", "id": "x", "time": 0, "user": "alice",
                 "cluster": "away", "service": "k", "verb": "read"}
            ],
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(result["replies"], [{"id": "x", "status": "not_found"}])
        self.assertEqual(result["service_lookups"], 1)
        self.assertEqual(result["remote_routes"], 0)
        self.assertEqual(result["certificates_issued"], 0)

    def test_local_credential_no_cache(self):
        payload = {
            "ttl": 5,
            "clusters": {"here": {"mode": "local", "services": {"k": True}}},
            "policies": {"alice": [{"cluster": "here", "verb": "read"}]},
            "events": [
                {"op": "request", "id": "x", "time": 0, "user": "alice",
                 "cluster": "here", "service": "k", "verb": "read"}
            ],
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(result["replies"], [{"id": "x", "status": "ok",
                                              "credential": "local", "route": "local"}])
        self.assertEqual(result["cache"], [])

    def test_cache_expiry_issues_new_cert(self):
        # ttl=5, first request at time 0 -> cert-1 expires 5. Second at time 5
        # (expires<=now) must issue cert-2.
        payload = {
            "ttl": 5,
            "clusters": {"away": {"mode": "remote", "services": {"k": True}}},
            "policies": {"alice": [{"cluster": "away", "verb": "read"}]},
            "events": [
                {"op": "request", "id": "a", "time": 0, "user": "alice",
                 "cluster": "away", "service": "k", "verb": "read"},
                {"op": "request", "id": "b", "time": 5, "user": "alice",
                 "cluster": "away", "service": "k", "verb": "read"},
            ],
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(result["replies"][0]["credential"], "cert-1")
        self.assertEqual(result["replies"][1]["credential"], "cert-2")
        self.assertEqual(result["certificates_issued"], 2)
        self.assertEqual(result["cache"], [{"user": "alice", "cluster": "away",
                                            "service": "k", "credential": "cert-2",
                                            "expires": 10}])

    def test_policy_event_replaces_allow_list(self):
        # policy event replaces the user's allow list entirely.
        payload = {
            "ttl": 5,
            "clusters": {"away": {"mode": "remote", "services": {"k": True}}},
            "policies": {"alice": [{"cluster": "away", "verb": "read"}]},
            "events": [
                {"op": "policy", "time": 0, "user": "alice",
                 "allow": [{"cluster": "away", "verb": "write"}]},
                {"op": "request", "id": "x", "time": 1, "user": "alice",
                 "cluster": "away", "service": "k", "verb": "read"},
            ],
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(result["replies"], [{"id": "x", "status": "denied"}])

    def test_service_event_updates_availability(self):
        payload = {
            "ttl": 5,
            "clusters": {"away": {"mode": "remote", "services": {"k": True}}},
            "policies": {"alice": [{"cluster": "away", "verb": "read"}]},
            "events": [
                {"op": "service", "time": 0, "cluster": "away",
                 "service": "k", "available": False},
                {"op": "request", "id": "x", "time": 1, "user": "alice",
                 "cluster": "away", "service": "k", "verb": "read"},
            ],
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(result["replies"], [{"id": "x", "status": "not_found"}])

    def test_wildcard_service_rule(self):
        payload = {
            "ttl": 5,
            "clusters": {"away": {"mode": "remote", "services": {"k": True}}},
            "policies": {"alice": [{"cluster": "away", "verb": "read", "service": "*"}]},
            "events": [
                {"op": "request", "id": "x", "time": 0, "user": "alice",
                 "cluster": "away", "service": "k", "verb": "read"},
            ],
        }
        result = call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(result["replies"][0]["status"], "ok")

    def test_transform_does_not_mutate_input(self):
        import copy
        payload = {
            "ttl": 5,
            "clusters": {"away": {"mode": "remote", "services": {"k": True}}},
            "policies": {"alice": [{"cluster": "away", "verb": "read"}]},
            "events": [
                {"op": "request", "id": "x", "time": 0, "user": "alice",
                 "cluster": "away", "service": "k", "verb": "read"},
            ],
        }
        before = copy.deepcopy(payload)
        call_candidate("solution.py", "transform", args=[payload])
        self.assertEqual(payload, before)


if __name__ == "__main__":
    unittest.main()
