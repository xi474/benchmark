import unittest

API_BOUNDARY_REQUIREMENTS = [
    {
        "target_path": "domains/classification/transform.py",
        "function": "transform",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": True,
                "contract_path": "README.md",
                "requirement_quote": "未知额外字段可忽略，但其中非有限JSON仍非法",
            },
            "invalid_payload_type": {
                "applicable": True,
                "contract_path": "README.md",
                "requirement_quote": "仅对象/数组顶层合法；非法JSON、其他顶层类型和任意嵌套NaN/Infinity抛ValueError",
            },
        },
    },
    {
        "target_path": "domains/amounts/transform.py",
        "function": "transform",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": True,
                "contract_path": "README.md",
                "requirement_quote": "未知额外字段可忽略，但其中非有限JSON仍非法",
            },
            "invalid_payload_type": {
                "applicable": True,
                "contract_path": "README.md",
                "requirement_quote": "仅对象/数组顶层合法；非法JSON、其他顶层类型和任意嵌套NaN/Infinity抛ValueError",
            },
        },
    },
    {
        "target_path": "views/archive/transform.py",
        "function": "transform",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": True,
                "contract_path": "README.md",
                "requirement_quote": "未知额外字段可忽略，但其中非有限JSON仍非法",
            },
            "invalid_payload_type": {
                "applicable": True,
                "contract_path": "README.md",
                "requirement_quote": "仅对象/数组顶层合法；非法JSON、其他顶层类型和任意嵌套NaN/Infinity抛ValueError",
            },
        },
    },
]


class TestClassification(unittest.TestCase):
    def test_classification_priority(self):
        docs = {
            "documents": [
                {"id": "a", "filename": "x.txt", "text": "a receipt and an INVOICE"},
                {"id": "b", "filename": "y.txt", "text": "just a receipt"},
                {"id": "c", "filename": "z.txt", "text": "nothing here"},
            ]
        }
        contract = {"name": "classification", "operation": "invoice_classification",
                    "inputs": ["inputs/case.json"], "output": "outputs/classification.json"}
        result = call_candidate("domains/classification/transform.py", "transform",
                                args=[[docs], contract])
        self.assertEqual(result["name"], "classification")
        self.assertEqual(result["result"]["classes"],
                         {"a": "invoice", "b": "receipt", "c": "other"})

    def test_classification_duplicate_id(self):
        docs = {"documents": [
            {"id": "a", "filename": "x.txt", "text": "invoice"},
            {"id": "a", "filename": "y.txt", "text": "receipt"},
        ]}
        contract = {"name": "classification", "operation": "invoice_classification",
                    "inputs": ["inputs/case.json"], "output": "outputs/classification.json"}
        with self.assertRaises(CandidateCallError) as cm:
            call_candidate("domains/classification/transform.py", "transform",
                           args=[[docs], contract])
        self.assertEqual(cm.exception.details["failure_phase"], "candidate_exception")
        self.assertEqual(cm.exception.details["error_type"], "ValueError")

    def test_classification_api_boundary(self):
        docs = {"documents": [
            {"id": "a", "filename": "x.txt", "text": "invoice"},
        ]}
        contract = {"name": "classification", "operation": "invoice_classification",
                    "inputs": ["inputs/case.json"], "output": "outputs/classification.json"}
        for rule in ("invalid_payload_type", "nonfinite_unknown_field"):
            with self.subTest(rule=rule):
                check_api_boundary(
                    "domains/classification/transform.py", rule=rule,
                    contract_path="README.md",
                    requirement_quote=API_BOUNDARY_REQUIREMENTS[0]["rules"][rule]["requirement_quote"],
                    args=[[docs], contract])


class TestAmounts(unittest.TestCase):
    def test_amounts_total_priority_and_vat_default(self):
        docs = {"documents": [
            {"id": "a", "filename": "x.txt",
             "text": "Total: USD 1,200.50\nAmount Due: 12.00\n"},
            {"id": "b", "filename": "y.txt",
             "text": "Amount Due: 99.99\nVAT: 5.00\n"},
        ]}
        contract = {"name": "amounts", "operation": "invoice_amounts",
                    "inputs": ["inputs/case.json"], "output": "outputs/amounts.json"}
        result = call_candidate("domains/amounts/transform.py", "transform",
                                args=[[docs], contract])
        self.assertEqual(result["result"]["amounts"],
                         {"a": {"total": "1200.50", "vat": "0.00"},
                          "b": {"total": "99.99", "vat": "5.00"}})

    def test_amounts_duplicate_total(self):
        docs = {"documents": [
            {"id": "a", "filename": "x.txt",
             "text": "Total: 1.00\nTotal: 2.00\n"},
        ]}
        contract = {"name": "amounts", "operation": "invoice_amounts",
                    "inputs": ["inputs/case.json"], "output": "outputs/amounts.json"}
        with self.assertRaises(CandidateCallError) as cm:
            call_candidate("domains/amounts/transform.py", "transform",
                           args=[[docs], contract])
        self.assertEqual(cm.exception.details["failure_phase"], "candidate_exception")
        self.assertEqual(cm.exception.details["error_type"], "ValueError")

    def test_amounts_invalid_amount(self):
        docs = {"documents": [
            {"id": "a", "filename": "x.txt", "text": "Total: 1.2\n"},
        ]}
        contract = {"name": "amounts", "operation": "invoice_amounts",
                    "inputs": ["inputs/case.json"], "output": "outputs/amounts.json"}
        with self.assertRaises(CandidateCallError) as cm:
            call_candidate("domains/amounts/transform.py", "transform",
                           args=[[docs], contract])
        self.assertEqual(cm.exception.details["failure_phase"], "candidate_exception")
        self.assertEqual(cm.exception.details["error_type"], "ValueError")

    def test_amounts_api_boundary(self):
        docs = {"documents": [
            {"id": "a", "filename": "x.txt", "text": "Total: 1.00\n"},
        ]}
        contract = {"name": "amounts", "operation": "invoice_amounts",
                    "inputs": ["inputs/case.json"], "output": "outputs/amounts.json"}
        for rule in ("invalid_payload_type", "nonfinite_unknown_field"):
            with self.subTest(rule=rule):
                check_api_boundary(
                    "domains/amounts/transform.py", rule=rule,
                    contract_path="README.md",
                    requirement_quote=API_BOUNDARY_REQUIREMENTS[1]["rules"][rule]["requirement_quote"],
                    args=[[docs], contract])


class TestArchive(unittest.TestCase):
    def test_archive_totals_and_rows(self):
        documents = {"documents": [
            {"id": "a", "filename": "x.txt", "text": "Invoice\nTotal: 10.00\n"},
            {"id": "b", "filename": "y.txt", "text": "Receipt\nTotal: 20.00\n"},
            {"id": "c", "filename": "z.txt", "text": "notes\n"},
        ]}
        classification = {"classes": {"a": "invoice", "b": "receipt", "c": "other"}}
        amounts = {"amounts": {
            "a": {"total": "10.00", "vat": "1.00"},
            "b": {"total": "20.00", "vat": "2.00"},
            "c": {"total": None, "vat": "0.00"},
        }}
        contract = {"name": "archive", "operation": "invoice_archive_summary",
                    "inputs": ["inputs/case.json", "outputs/classification.json",
                               "outputs/amounts.json"],
                    "output": "outputs/archive.json"}
        result = call_candidate("views/archive/transform.py", "transform",
                                args=[[documents, classification, amounts], contract])
        r = result["result"]
        self.assertEqual(r["totals"], {"invoice": "10.00", "receipt": "20.00"})
        self.assertEqual([row["id"] for row in r["rows"]], ["a", "b", "c"])
        self.assertEqual(r["rows"][2]["total"], None)
        self.assertTrue(r["csv"].startswith("id,filename,kind,total,vat\n"))

    def test_archive_invoice_missing_total(self):
        documents = {"documents": [
            {"id": "a", "filename": "x.txt", "text": "Invoice\n"},
        ]}
        classification = {"classes": {"a": "invoice"}}
        amounts = {"amounts": {"a": {"total": None, "vat": "0.00"}}}
        contract = {"name": "archive", "operation": "invoice_archive_summary",
                    "inputs": ["inputs/case.json", "outputs/classification.json",
                               "outputs/amounts.json"],
                    "output": "outputs/archive.json"}
        with self.assertRaises(CandidateCallError) as cm:
            call_candidate("views/archive/transform.py", "transform",
                           args=[[documents, classification, amounts], contract])
        self.assertEqual(cm.exception.details["failure_phase"], "candidate_exception")
        self.assertEqual(cm.exception.details["error_type"], "ValueError")

    def test_archive_api_boundary(self):
        documents = {"documents": [
            {"id": "a", "filename": "x.txt", "text": "Invoice\nTotal: 10.00\n"},
        ]}
        classification = {"classes": {"a": "invoice"}}
        amounts = {"amounts": {"a": {"total": "10.00", "vat": "0.00"}}}
        contract = {"name": "archive", "operation": "invoice_archive_summary",
                    "inputs": ["inputs/case.json", "outputs/classification.json",
                               "outputs/amounts.json"],
                    "output": "outputs/archive.json"}
        for rule in ("invalid_payload_type", "nonfinite_unknown_field"):
            with self.subTest(rule=rule):
                check_api_boundary(
                    "views/archive/transform.py", rule=rule,
                    contract_path="README.md",
                    requirement_quote=API_BOUNDARY_REQUIREMENTS[2]["rules"][rule]["requirement_quote"],
                    args=[[documents, classification, amounts], contract])


if __name__ == "__main__":
    unittest.main()
