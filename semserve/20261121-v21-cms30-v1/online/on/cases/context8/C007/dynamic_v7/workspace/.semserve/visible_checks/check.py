import unittest

# Injected by the visible-contract SDK runner.
try:
    from visible_contract_check_sdk import call_candidate, CandidateCallError, check_api_boundary
except Exception:
    call_candidate = None
    CandidateCallError = Exception
    check_api_boundary = None


class TestTransformContract(unittest.TestCase):
    """Independent visible-contract checks for C007 transform."""

    def test_output_shape_and_every_record_once(self):
        # Output contract: {clusters:[[record_id,...],...]}, each record exactly once.
        payload = {"records": [], "ambiguous_names": []}
        left = [
            [0, {"id": "a1", "first": "alice", "last": "smith", "dob": "1990-01-01",
                 "ssn": "123456789", "mail": "aliceexampleorg", "phone": "5550000001",
                 "address": "1mainst"}],
        ]
        right = [
            [1, {"id": "a2", "first": "bob", "last": "jones", "dob": "1985-05-05",
                 "ssn": "", "mail": "bobjonesexampleorg", "phone": "5550000002",
                 "address": "2mainst"}],
        ]
        result = call_candidate("integration.py", "combine", args=[payload, left, right])
        self.assertIsInstance(result, dict)
        self.assertIn("clusters", result)
        clusters = result["clusters"]
        self.assertIsInstance(clusters, list)
        ids = [i for c in clusters for i in c]
        self.assertEqual(len(ids), len(set(ids)), "records must appear exactly once")
        self.assertEqual(set(ids), {"a1", "a2"})

    def test_same_person_clustered(self):
        # Two records of the same person (matching non-ambiguous name + dob)
        # must be in the same cluster.
        payload = {"records": [], "ambiguous_names": []}
        left = [
            [0, {"id": "a1", "first": "alice", "last": "smith", "dob": "1990-01-01",
                 "ssn": "123456789", "mail": "aliceexampleorg", "phone": "5550000001",
                 "address": "1mainst"}],
        ]
        right = [
            [1, {"id": "a2", "first": "alice", "last": "smith", "dob": "1990-01-01",
                 "ssn": "", "mail": "aliceexampleorg", "phone": "5550000001",
                 "address": "1mainst"}],
        ]
        result = call_candidate("integration.py", "combine", args=[payload, left, right])
        clusters = result["clusters"]
        self.assertEqual(len(clusters), 1)
        self.assertEqual(set(clusters[0]), {"a1", "a2"})

    def test_ambiguous_name_not_merged_unconditionally(self):
        # 'pat' is ambiguous; two records sharing only the ambiguous nickname
        # and family fields must NOT be merged.
        payload = {"records": [], "ambiguous_names": ["pat"]}
        left = [
            [0, {"id": "p1", "first": "pat", "last": "family", "dob": "1970-01-01",
                 "ssn": "1111", "mail": "", "phone": "5550000000", "address": "1mainst"}],
            [1, {"id": "p2", "first": "pat", "last": "family", "dob": "1970-01-01",
                 "ssn": "2222", "mail": "", "phone": "5550000000", "address": "1mainst"}],
        ]
        result = call_candidate("integration.py", "combine", args=[payload, left, []])
        clusters = result["clusters"]
        self.assertEqual(len(clusters), 2, "ambiguous 'pat' records must stay separate")

    def test_full_ssn_links_records(self):
        # A 9-digit government id is accurate and unique; records sharing it
        # must be merged even with different first names.
        payload = {"records": [], "ambiguous_names": []}
        left = [
            [0, {"id": "x1", "first": "robert", "last": "family", "dob": "1971-02-02",
                 "ssn": "734688346", "mail": "", "phone": "5550000001", "address": "2mainst"}],
            [1, {"id": "x2", "first": "robbie", "last": "family", "dob": "1971-02-02",
                 "ssn": "734688346", "mail": "", "phone": "5550000001", "address": "2mainst"}],
        ]
        result = call_candidate("integration.py", "combine", args=[payload, left, []])
        self.assertEqual(len(result["clusters"]), 1)


if __name__ == "__main__":
    unittest.main()
