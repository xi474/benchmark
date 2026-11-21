import unittest

API_BOUNDARY_REQUIREMENTS = [
    {
        "target_path": "domains/fstab/transform.py",
        "function": "transform",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": True,
                "contract_path": "README.md",
                "requirement_quote": "未知额外字段可忽略，但其中非有限JSON仍非法。",
            },
            "invalid_payload_type": {
                "applicable": True,
                "contract_path": "README.md",
                "requirement_quote": "仅对象/数组顶层合法；非法JSON、其他顶层类型和任意嵌套NaN/Infinity抛ValueError。",
            },
        },
    },
    {
        "target_path": "domains/aix/transform.py",
        "function": "transform",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": True,
                "contract_path": "README.md",
                "requirement_quote": "未知额外字段可忽略，但其中非有限JSON仍非法。",
            },
            "invalid_payload_type": {
                "applicable": True,
                "contract_path": "README.md",
                "requirement_quote": "仅对象/数组顶层合法；非法JSON、其他顶层类型和任意嵌套NaN/Infinity抛ValueError。",
            },
        },
    },
    {
        "target_path": "domains/mount/transform.py",
        "function": "transform",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": True,
                "contract_path": "README.md",
                "requirement_quote": "未知额外字段可忽略，但其中非有限JSON仍非法。",
            },
            "invalid_payload_type": {
                "applicable": True,
                "contract_path": "README.md",
                "requirement_quote": "仅对象/数组顶层合法；非法JSON、其他顶层类型和任意嵌套NaN/Infinity抛ValueError。",
            },
        },
    },
    {
        "target_path": "views/merged/transform.py",
        "function": "transform",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": True,
                "contract_path": "README.md",
                "requirement_quote": "未知额外字段可忽略，但其中非有限JSON仍非法。",
            },
            "invalid_payload_type": {
                "applicable": True,
                "contract_path": "README.md",
                "requirement_quote": "仅对象/数组顶层合法；非法JSON、其他顶层类型和任意嵌套NaN/Infinity抛ValueError。",
            },
        },
    },
]


class TestFstabParse(unittest.TestCase):
    def test_fstab_parse_basic(self):
        payload = {"fstab": "/dev/sda1 / ext4 rw 0 1\n"}
        contract = {"name": "fstab", "operation": "fstab_parse", "inputs": ["x"], "output": "y"}
        result = call_candidate("domains/fstab/transform.py", "transform", args=[[payload], contract])
        self.assertEqual(result["name"], "fstab")
        self.assertEqual(result["result"]["records"], [
            {"device": "/dev/sda1", "mount": "/", "fstype": "ext4", "options": ["rw"]},
        ])

    def test_fstab_escape_and_options(self):
        payload = {"fstab": "/dev/x /with\\040space xfs ro,nosuid\n"}
        contract = {"name": "fstab", "operation": "fstab_parse", "inputs": ["x"], "output": "y"}
        result = call_candidate("domains/fstab/transform.py", "transform", args=[[payload], contract])
        rec = result["result"]["records"][0]
        self.assertEqual(rec["mount"], "/with space")
        self.assertEqual(rec["options"], ["nosuid", "ro"])


class TestAixParse(unittest.TestCase):
    def test_aix_parse_defaults(self):
        payload = {"aix": "/data:\n  dev = /dev/aix\n"}
        contract = {"name": "aix", "operation": "aix_parse", "inputs": ["x"], "output": "y"}
        result = call_candidate("domains/aix/transform.py", "transform", args=[[payload], contract])
        self.assertEqual(result["result"]["records"], [
            {"device": "/dev/aix", "mount": "/data", "fstype": "jfs2", "options": ["rw"]},
        ])

    def test_aix_missing_dev_raises(self):
        payload = {"aix": "/data:\n  vfs = jfs2\n"}
        contract = {"name": "aix", "operation": "aix_parse", "inputs": ["x"], "output": "y"}
        with self.assertRaises(CandidateCallError) as cm:
            call_candidate("domains/aix/transform.py", "transform", args=[[payload], contract])
        self.assertEqual(cm.exception.details["failure_phase"], "candidate_exception")
        self.assertEqual(cm.exception.details["error_type"], "ValueError")


class TestMountParse(unittest.TestCase):
    def test_mount_parse_basic(self):
        payload = {"mount": "/dev/sda1 on / type ext4 (rw,relatime)\n"}
        contract = {"name": "mount", "operation": "mount_parse", "inputs": ["x"], "output": "y"}
        result = call_candidate("domains/mount/transform.py", "transform", args=[[payload], contract])
        self.assertEqual(result["result"]["records"], [
            {"device": "/dev/sda1", "mount": "/", "fstype": "ext4", "options": ["relatime", "rw"]},
        ])

    def test_mount_empty_options_raises(self):
        payload = {"mount": "/dev/sda1 on / type ext4 ()\n"}
        contract = {"name": "mount", "operation": "mount_parse", "inputs": ["x"], "output": "y"}
        with self.assertRaises(CandidateCallError) as cm:
            call_candidate("domains/mount/transform.py", "transform", args=[[payload], contract])
        self.assertEqual(cm.exception.details["failure_phase"], "candidate_exception")
        self.assertEqual(cm.exception.details["error_type"], "ValueError")


class TestMerged(unittest.TestCase):
    def test_merge_priority_and_conflict(self):
        fstab = {"name": "fstab", "result": {"records": [
            {"device": "/dev/a", "mount": "/m", "fstype": "ext4", "options": ["rw"]},
        ]}}
        aix = {"name": "aix", "result": {"records": [
            {"device": "/dev/b", "mount": "/m", "fstype": "xfs", "options": ["ro"]},
        ]}}
        mount = {"name": "mount", "result": {"records": []}}
        contract = {"name": "merged", "operation": "mount_merge", "inputs": ["a", "b", "c"], "output": "d"}
        result = call_candidate("views/merged/transform.py", "transform",
                                args=[[fstab, aix, mount], contract])
        self.assertEqual(result["result"]["records"][0]["source"], "fstab")
        self.assertEqual(result["result"]["records"][0]["device"], "/dev/a")
        self.assertEqual(len(result["result"]["conflicts"]), 1)
        self.assertEqual(result["result"]["conflicts"][0]["mount"], "/m")
        self.assertEqual(len(result["result"]["conflicts"][0]["evidence"]), 2)

    def test_merge_identical_no_conflict(self):
        rec = {"device": "/dev/a", "mount": "/m", "fstype": "ext4", "options": ["rw"]}
        fstab = {"name": "fstab", "result": {"records": [dict(rec)]}}
        aix = {"name": "aix", "result": {"records": [dict(rec)]}}
        mount = {"name": "mount", "result": {"records": []}}
        contract = {"name": "merged", "operation": "mount_merge", "inputs": ["a", "b", "c"], "output": "d"}
        result = call_candidate("views/merged/transform.py", "transform",
                                args=[[fstab, aix, mount], contract])
        self.assertEqual(result["result"]["conflicts"], [])
        self.assertEqual(len(result["result"]["records"]), 1)


class TestApiBoundary(unittest.TestCase):
    def test_api_boundary_probes(self):
        fstab_payload = {"fstab": "/dev/sda1 / ext4 rw 0 1\n"}
        aix_payload = {"aix": "/data:\n  dev = /dev/aix\n"}
        mount_payload = {"mount": "/dev/sda1 on / type ext4 (rw)\n"}
        merged_payloads = [
            {"name": "fstab", "result": {"records": []}},
            {"name": "aix", "result": {"records": []}},
            {"name": "mount", "result": {"records": []}},
        ]
        contract = {"name": "x", "operation": "op", "inputs": ["a"], "output": "b"}

        cases = [
            ("domains/fstab/transform.py", "nonfinite_unknown_field", [fstab_payload]),
            ("domains/fstab/transform.py", "invalid_payload_type", [fstab_payload]),
            ("domains/aix/transform.py", "nonfinite_unknown_field", [aix_payload]),
            ("domains/aix/transform.py", "invalid_payload_type", [aix_payload]),
            ("domains/mount/transform.py", "nonfinite_unknown_field", [mount_payload]),
            ("domains/mount/transform.py", "invalid_payload_type", [mount_payload]),
            ("views/merged/transform.py", "nonfinite_unknown_field", merged_payloads),
            ("views/merged/transform.py", "invalid_payload_type", merged_payloads),
        ]
        for target, rule, args in cases:
            with self.subTest(target=target, rule=rule):
                check_api_boundary(
                    target,
                    rule=rule,
                    contract_path="README.md",
                    requirement_quote="未知额外字段可忽略，但其中非有限JSON仍非法。",
                    args=args,
                )


if __name__ == "__main__":
    unittest.main()
