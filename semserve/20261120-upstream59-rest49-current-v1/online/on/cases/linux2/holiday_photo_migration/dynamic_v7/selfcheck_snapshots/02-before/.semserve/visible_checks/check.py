import unittest

API_BOUNDARY_REQUIREMENTS = [
    {
        "target_path": "products/classify/transform.py",
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
        "target_path": "products/migrate/transform.py",
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
        "target_path": "products/outbox/transform.py",
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


class TestClassify(unittest.TestCase):
    def test_classify_selection_and_missing(self):
        payload = {
            "destination": "holiday",
            "festivals": ["spring", "summer", "winter"],
            "files": [
                {"path": "photos/day0/img.jpg", "hex": "00"},
                {"path": "photos/day1/img.jpg", "hex": "00"},
                {"path": "notes.txt", "hex": "00"},
            ],
            "photos": [
                {"path": "photos/day0/img.jpg", "festival": "spring"},
                {"path": "photos/day1/img.jpg", "festival": "autumn"},
            ],
            "recipient": "friend47",
        }
        contract = {"name": "classify", "operation": "photo_classification",
                    "inputs": ["inputs/case.json"], "output": "outputs/classify.json"}
        result = call_candidate("products/classify/transform.py", "transform",
                                args=[[payload], contract])
        self.assertEqual(result["name"], "classify")
        self.assertEqual(result["result"]["selected"],
                         [{"path": "photos/day0/img.jpg", "festival": "spring"}])
        self.assertEqual(result["result"]["missing"], ["summer", "winter"])

    def test_classify_duplicate_photo_path_rejected(self):
        payload = {
            "destination": "holiday",
            "festivals": ["spring"],
            "files": [{"path": "a.jpg", "hex": "00"}],
            "photos": [
                {"path": "a.jpg", "festival": "spring"},
                {"path": "a.jpg", "festival": "spring"},
            ],
            "recipient": "r",
        }
        contract = {"name": "classify", "operation": "photo_classification",
                    "inputs": ["inputs/case.json"], "output": "outputs/classify.json"}
        with self.assertRaises(CandidateCallError) as cm:
            call_candidate("products/classify/transform.py", "transform",
                           args=[[payload], contract])
        self.assertEqual(cm.exception.details["failure_phase"], "candidate_exception")
        self.assertEqual(cm.exception.details["error_type"], "ValueError")


    def test_classify_api_boundary(self):
        payload = {
            "destination": "holiday",
            "festivals": ["spring"],
            "files": [{"path": "a.jpg", "hex": "00"}],
            "photos": [{"path": "a.jpg", "festival": "spring"}],
            "recipient": "r",
        }
        contract = {"name": "classify", "operation": "photo_classification",
                    "inputs": ["inputs/case.json"], "output": "outputs/classify.json"}
        for rule in ("invalid_payload_type", "nonfinite_unknown_field"):
            with self.subTest(rule=rule):
                check_api_boundary(
                    "products/classify/transform.py", rule=rule,
                    contract_path="README.md",
                    requirement_quote=API_BOUNDARY_REQUIREMENTS[0]["rules"][rule]["requirement_quote"],
                    args=[[payload], contract],
                )


class TestMigrate(unittest.TestCase):
    def test_migrate_moves_and_files(self):
        snapshot = {
            "destination": "holiday",
            "festivals": ["spring"],
            "files": [
                {"path": "photos/a.jpg", "hex": "aa"},
                {"path": "notes.txt", "hex": "00"},
            ],
            "photos": [{"path": "photos/a.jpg", "festival": "spring"}],
            "recipient": "r",
        }
        classification = {"selected": [{"path": "photos/a.jpg", "festival": "spring"}],
                          "missing": []}
        contract = {"name": "migrate", "operation": "photo_migration",
                    "inputs": ["inputs/case.json", "outputs/classify.json"],
                    "output": "outputs/migrate.json"}
        result = call_candidate("products/migrate/transform.py", "transform",
                                args=[[snapshot, classification], contract])
        self.assertEqual(result["result"]["moves"],
                         [{"from": "photos/a.jpg", "to": "holiday/photos/a.jpg",
                           "festival": "spring"}])
        self.assertEqual(result["result"]["files"],
                         [{"path": "holiday/photos/a.jpg", "hex": "aa"},
                          {"path": "notes.txt", "hex": "00"}])


    def test_migrate_api_boundary(self):
        snapshot = {
            "destination": "holiday",
            "festivals": ["spring"],
            "files": [{"path": "photos/a.jpg", "hex": "aa"}],
            "photos": [{"path": "photos/a.jpg", "festival": "spring"}],
            "recipient": "r",
        }
        classification = {"selected": [{"path": "photos/a.jpg", "festival": "spring"}],
                          "missing": []}
        contract = {"name": "migrate", "operation": "photo_migration",
                    "inputs": ["inputs/case.json", "outputs/classify.json"],
                    "output": "outputs/migrate.json"}
        for rule in ("invalid_payload_type", "nonfinite_unknown_field"):
            with self.subTest(rule=rule):
                check_api_boundary(
                    "products/migrate/transform.py", rule=rule,
                    contract_path="README.md",
                    requirement_quote=API_BOUNDARY_REQUIREMENTS[1]["rules"][rule]["requirement_quote"],
                    args=[[snapshot, classification], contract],
                )


class TestOutbox(unittest.TestCase):
    def test_outbox_message_and_attachments(self):
        snapshot = {"recipient": "friend47"}
        classification = {"missing": ["winter"]}
        migration = {"moves": [{"to": "holiday/photos/a.jpg"},
                               {"to": "holiday/photos/b.jpg"}]}
        contract = {"name": "outbox", "operation": "photo_outbox",
                    "inputs": ["inputs/case.json", "outputs/classify.json",
                               "outputs/migrate.json"],
                    "output": "outputs/outbox.json"}
        result = call_candidate("products/outbox/transform.py", "transform",
                                args=[[snapshot, classification, migration], contract])
        self.assertEqual(result["result"]["to"], "friend47")
        self.assertEqual(result["result"]["attachments"],
                         ["holiday/photos/a.jpg", "holiday/photos/b.jpg"])
        self.assertEqual(result["result"]["missing"], ["winter"])
        self.assertEqual(result["result"]["message"], "Missing: winter")

    def test_outbox_no_missing_message(self):
        snapshot = {"recipient": "friend47"}
        classification = {"missing": []}
        migration = {"moves": []}
        contract = {"name": "outbox", "operation": "photo_outbox",
                    "inputs": ["inputs/case.json", "outputs/classify.json",
                               "outputs/migrate.json"],
                    "output": "outputs/outbox.json"}
        result = call_candidate("products/outbox/transform.py", "transform",
                                args=[[snapshot, classification, migration], contract])
        self.assertEqual(result["result"]["message"], "Photos ready")
        self.assertEqual(result["result"]["attachments"], [])


    def test_outbox_api_boundary(self):
        snapshot = {"recipient": "friend47"}
        classification = {"missing": []}
        migration = {"moves": []}
        contract = {"name": "outbox", "operation": "photo_outbox",
                    "inputs": ["inputs/case.json", "outputs/classify.json",
                               "outputs/migrate.json"],
                    "output": "outputs/outbox.json"}
        for rule in ("invalid_payload_type", "nonfinite_unknown_field"):
            with self.subTest(rule=rule):
                check_api_boundary(
                    "products/outbox/transform.py", rule=rule,
                    contract_path="README.md",
                    requirement_quote=API_BOUNDARY_REQUIREMENTS[2]["rules"][rule]["requirement_quote"],
                    args=[[snapshot, classification, migration], contract],
                )


if __name__ == "__main__":
    unittest.main()
