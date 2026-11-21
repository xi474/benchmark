import unittest


class TestTransformContract(unittest.TestCase):
    def _call(self, payload):
        return call_candidate("solution.py", "transform", args=[payload])

    def test_denied_request_no_service_lookup(self):
        payload = {
            "ttl": 5,
            "clusters": {"c": {"mode": "remote", "services": {"s": True}}},
            "policies": {"u": [{"cluster": "c", "verb": "read"}]},
            "events": [
                {"op": "request", "id": "r1", "time": 0, "user": "u",
                 "cluster": "c", "service": "s", "verb": "write"},
            ],
        }
        out = self._call(payload)
        self.assertEqual(out["replies"], [{"id": "r1", "status": "denied"}])
        self.assertEqual(out["authorizer_calls"], 1)
        self.assertEqual(out["service_lookups"], 0)
        self.assertEqual(out["remote_routes"], 0)
        self.assertEqual(out["certificates_issued"], 0)
        self.assertEqual(out["cache"], [])

    def test_not_found_no_certificate(self):
        payload = {
            "ttl": 5,
            "clusters": {"c": {"mode": "remote", "services": {"s": False}}},
            "policies": {"u": [{"cluster": "c", "verb": "read"}]},
            "events": [
                {"op": "request", "id": "r1", "time": 0, "user": "u",
                 "cluster": "c", "service": "s", "verb": "read"},
            ],
        }
        out = self._call(payload)
        self.assertEqual(out["replies"], [{"id": "r1", "status": "not_found"}])
        self.assertEqual(out["service_lookups"], 1)
        self.assertEqual(out["certificates_issued"], 0)
        self.assertEqual(out["cache"], [])

    def test_local_route_no_cache(self):
        payload = {
            "ttl": 5,
            "clusters": {"c": {"mode": "local", "services": {"s": True}}},
            "policies": {"u": [{"cluster": "c", "verb": "read"}]},
            "events": [
                {"op": "request", "id": "r1", "time": 0, "user": "u",
                 "cluster": "c", "service": "s", "verb": "read"},
            ],
        }
        out = self._call(payload)
        self.assertEqual(out["replies"], [{
            "id": "r1", "status": "ok", "credential": "local", "route": "local"}])
        self.assertEqual(out["certificates_issued"], 0)
        self.assertEqual(out["cache"], [])

    def test_cache_expiry_issues_new_cert(self):
        payload = {
            "ttl": 2,
            "clusters": {"c": {"mode": "remote", "services": {"s": True}}},
            "policies": {"u": [{"cluster": "c", "verb": "read"}]},
            "events": [
                {"op": "request", "id": "r1", "time": 0, "user": "u",
                 "cluster": "c", "service": "s", "verb": "read"},
                {"op": "request", "id": "r2", "time": 2, "user": "u",
                 "cluster": "c", "service": "s", "verb": "read"},
            ],
        }
        out = self._call(payload)
        self.assertEqual(out["replies"][0]["credential"], "cert-1")
        self.assertEqual(out["replies"][1]["credential"], "cert-2")
        self.assertEqual(out["certificates_issued"], 2)
        self.assertEqual(len(out["cache"]), 1)
        self.assertEqual(out["cache"][0]["credential"], "cert-2")
        self.assertEqual(out["cache"][0]["expires"], 4)

    def test_policy_event_replaces_allow_list(self):
        payload = {
            "ttl": 5,
            "clusters": {"c": {"mode": "local", "services": {"s": True}}},
            "policies": {"u": [{"cluster": "c", "verb": "read"}]},
            "events": [
                {"op": "policy", "time": 0, "user": "u",
                 "allow": [{"cluster": "c", "verb": "write"}]},
                {"op": "request", "id": "r1", "time": 1, "user": "u",
                 "cluster": "c", "service": "s", "verb": "read"},
            ],
        }
        out = self._call(payload)
        self.assertEqual(out["replies"], [{"id": "r1", "status": "denied"}])

    def test_service_event_updates_availability(self):
        payload = {
            "ttl": 5,
            "clusters": {"c": {"mode": "remote", "services": {"s": True}}},
            "policies": {"u": [{"cluster": "c", "verb": "read"}]},
            "events": [
                {"op": "service", "time": 0, "cluster": "c", "service": "s",
                 "available": False},
                {"op": "request", "id": "r1", "time": 1, "user": "u",
                 "cluster": "c", "service": "s", "verb": "read"},
            ],
        }
        out = self._call(payload)
        self.assertEqual(out["replies"], [{"id": "r1", "status": "not_found"}])

    def test_transform_does_not_mutate_input(self):
        import copy
        payload = {
            "ttl": 5,
            "clusters": {"c": {"mode": "remote", "services": {"s": True}}},
            "policies": {"u": [{"cluster": "c", "verb": "read"}]},
            "events": [
                {"op": "request", "id": "r1", "time": 0, "user": "u",
                 "cluster": "c", "service": "s", "verb": "read"},
            ],
        }
        before = copy.deepcopy(payload)
        self._call(payload)
        self.assertEqual(payload, before)


if __name__ == "__main__":
    unittest.main()
