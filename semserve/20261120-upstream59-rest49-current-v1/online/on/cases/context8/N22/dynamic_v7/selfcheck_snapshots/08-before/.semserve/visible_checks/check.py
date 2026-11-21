import unittest

API_BOUNDARY_REQUIREMENTS = [
    {
        "target_path": "products/object_scan/engine.py",
        "function": "transform",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": False,
                "contract_path": "products/object_scan/SPEC.md",
                "requirement_quote": "仅考查公开合法输入域与明确业务拒绝分支，不要求任意畸形输入、额外字段递归检查、异常文案或隐藏兼容行为。",
                "reason": "SPEC explicitly excludes arbitrary malformed input and extra-field recursion checks.",
            },
            "invalid_payload_type": {
                "applicable": False,
                "contract_path": "products/object_scan/SPEC.md",
                "requirement_quote": "仅考查公开合法输入域与明确业务拒绝分支，不要求任意畸形输入、额外字段递归检查、异常文案或隐藏兼容行为。",
                "reason": "SPEC excludes arbitrary malformed input; no explicit ValueError rule for payload type.",
            },
        },
    },
    {
        "target_path": "products/cleaned_repo/engine.py",
        "function": "transform",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": False,
                "contract_path": "products/cleaned_repo/SPEC.md",
                "requirement_quote": "仅考查公开合法输入域与明确业务拒绝分支，不要求任意畸形输入、额外字段递归检查、异常文案或隐藏兼容行为。",
                "reason": "SPEC explicitly excludes arbitrary malformed input and extra-field recursion checks.",
            },
            "invalid_payload_type": {
                "applicable": False,
                "contract_path": "products/cleaned_repo/SPEC.md",
                "requirement_quote": "仅考查公开合法输入域与明确业务拒绝分支，不要求任意畸形输入、额外字段递归检查、异常文案或隐藏兼容行为。",
                "reason": "SPEC excludes arbitrary malformed input; no explicit ValueError rule for payload type.",
            },
        },
    },
    {
        "target_path": "products/recovery_report/engine.py",
        "function": "transform",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": False,
                "contract_path": "products/recovery_report/SPEC.md",
                "requirement_quote": "仅考查公开合法输入域与明确业务拒绝分支，不要求任意畸形输入、额外字段递归检查、异常文案或隐藏兼容行为。",
                "reason": "SPEC explicitly excludes arbitrary malformed input and extra-field recursion checks.",
            },
            "invalid_payload_type": {
                "applicable": False,
                "contract_path": "products/recovery_report/SPEC.md",
                "requirement_quote": "仅考查公开合法输入域与明确业务拒绝分支，不要求任意畸形输入、额外字段递归检查、异常文案或隐藏兼容行为。",
                "reason": "SPEC excludes arbitrary malformed input; no explicit ValueError rule for payload type.",
            },
        },
    },
]


class TestObjectScan(unittest.TestCase):
    def test_secret_recovered_from_bundle(self):
        import json
        from pathlib import Path
        root = Path(__file__).resolve().parents[2]
        req = json.loads((root / "inputs" / "request.json").read_text(encoding="utf-8"))
        payload = {"bundle": req["bundle"]}
        contract = {"bindings": {"bundle": "inputs/request.json#/bundle"}}
        result = call_candidate("products/object_scan/engine.py", "transform",
                                args=[payload, contract])
        self.assertIsInstance(result, dict)
        self.assertIn("secret", result)
        self.assertTrue(result["secret"].startswith("secret["))
        self.assertTrue(result["secret"].endswith("]"))


class TestRecoveryReport(unittest.TestCase):
    def test_report_shape_and_zero_remaining(self):
        import json
        from pathlib import Path
        root = Path(__file__).resolve().parents[2]
        scan = json.loads((root / "outputs" / "object_scan.json").read_text(encoding="utf-8"))
        cleaned = json.loads((root / "outputs" / "cleaned_repo.json").read_text(encoding="utf-8"))
        payload = {"scan": scan, "cleaned": cleaned}
        contract = {"bindings": {"scan": "outputs/object_scan.json#",
                                 "cleaned": "outputs/cleaned_repo.json#"}}
        result = call_candidate("products/recovery_report/engine.py", "transform",
                                args=[payload, contract])
        self.assertIsInstance(result, dict)
        self.assertEqual(result["secret"], scan["secret"])
        self.assertEqual(result["remaining_secret_objects"], 0)
        self.assertEqual(result["files"], cleaned["files"])
        self.assertEqual(result["messages"], cleaned["messages"])


if __name__ == "__main__":
    unittest.main()
