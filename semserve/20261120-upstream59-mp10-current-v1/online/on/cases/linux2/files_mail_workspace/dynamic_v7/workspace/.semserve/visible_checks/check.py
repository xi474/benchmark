import unittest

API_BOUNDARY_REQUIREMENTS = [
    {
        "target_path": "products/files/transform.py",
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
                "requirement_quote": "必需字段缺失、指定非法类型/重复/冲突均ValueError",
            },
        },
    },
    {
        "target_path": "products/mail/transform.py",
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
                "requirement_quote": "必需字段缺失、指定非法类型/重复/冲突均ValueError",
            },
        },
    },
    {
        "target_path": "products/reply/transform.py",
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
                "requirement_quote": "必需字段缺失、指定非法类型/重复/冲突均ValueError",
            },
        },
    },
    {
        "target_path": "products/commit/transform.py",
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
                "requirement_quote": "必需字段缺失、指定非法类型/重复/冲突均ValueError",
            },
        },
    },
]


class TestVisibleContract(unittest.TestCase):
    def test_files_download_archive_moves(self):
        payload = {
            "files": [
                {"path": "Downloads/a.PDF", "hex": "00"},
                {"path": "Downloads/b.jpg", "hex": "01"},
                {"path": "Downloads/nested/c.pdf", "hex": "02"},
                {"path": "Downloads/keep.exe", "hex": "03"},
            ],
            "download_prefix": "Downloads",
            "archive_prefix": "Archive",
            "extensions": {".pdf": "docs", ".jpg": "photos"},
        }
        contract = {"name": "files", "inputs": ["x"], "output": "y"}
        result = call_candidate(
            "products/files/transform.py", "transform", args=[[payload], contract]
        )
        self.assertEqual(
            result["result"]["moves"],
            [
                {"from": "Downloads/a.PDF", "to": "Archive/docs/a.PDF"},
                {"from": "Downloads/b.jpg", "to": "Archive/photos/b.jpg"},
            ],
        )

    def test_mail_trash_ids(self):
        payload = {
            "emails": [
                {"id": "m0", "date": "2026-10-30", "subject": "newsletter", "folder": "INBOX", "sender": "f", "thread_id": "t0"},
                {"id": "m1", "date": "2026-11-03", "subject": "Newsletter", "folder": "INBOX", "sender": "f", "thread_id": "t1"},
                {"id": "m2", "date": "2026-11-03", "subject": "news", "folder": "TRASH", "sender": "f", "thread_id": "t2"},
                {"id": "m3", "date": "2026-11-03", "subject": "Update", "folder": "INBOX", "sender": "f", "thread_id": "t3"},
            ],
            "month": "2026-11",
            "trash_keyword": "news",
        }
        contract = {"name": "mail", "inputs": ["x"], "output": "y"}
        result = call_candidate(
            "products/mail/transform.py", "transform", args=[[payload], contract]
        )
        self.assertEqual(result["result"]["trash_ids"], ["m1"])

    def test_reply_manager(self):
        payload = {
            "emails": [
                {"id": "m7", "date": "2026-11-03", "subject": "Update", "folder": "INBOX", "sender": "manager", "thread_id": "t7"},
            ],
            "reply_email_id": "m7",
            "manager": "manager",
            "reply_text": "Confirmed 47",
        }
        contract = {"name": "reply", "inputs": ["x"], "output": "y"}
        result = call_candidate(
            "products/reply/transform.py", "transform", args=[[payload], contract]
        )
        self.assertEqual(
            result["result"],
            {"email_id": "m7", "thread_id": "t7", "to": "manager", "text": "Confirmed 47"},
        )

    def test_reply_wrong_sender_raises(self):
        payload = {
            "emails": [
                {"id": "m7", "date": "2026-11-03", "subject": "Update", "folder": "INBOX", "sender": "friend", "thread_id": "t7"},
            ],
            "reply_email_id": "m7",
            "manager": "manager",
            "reply_text": "",
        }
        contract = {"name": "reply", "inputs": ["x"], "output": "y"}
        with self.assertRaises(CandidateCallError) as cm:
            call_candidate(
                "products/reply/transform.py", "transform", args=[[payload], contract]
            )
        self.assertEqual(cm.exception.details["failure_phase"], "candidate_exception")
        self.assertEqual(cm.exception.details["error_type"], "ValueError")

    def test_commit_conflict_raises(self):
        snapshot = {
            "files": [{"path": "Downloads/a.PDF", "hex": "00"}],
            "emails": [
                {"id": "m7", "date": "2026-11-03", "subject": "Update", "folder": "INBOX", "sender": "manager", "thread_id": "t7"},
            ],
        }
        files_result = {"moves": [{"from": "Downloads/a.PDF", "to": "Archive/docs/a.PDF"}]}
        mail_result = {"trash_ids": ["m7"]}
        reply_result = {"email_id": "m7", "thread_id": "t7", "to": "manager", "text": ""}
        contract = {"name": "commit", "inputs": ["a", "b", "c", "d"], "output": "y"}
        with self.assertRaises(CandidateCallError) as cm:
            call_candidate(
                "products/commit/transform.py",
                "transform",
                args=[[snapshot, files_result, mail_result, reply_result], contract],
            )
        self.assertEqual(cm.exception.details["failure_phase"], "candidate_exception")
        self.assertEqual(cm.exception.details["error_type"], "ValueError")

    def test_commit_replays_moves(self):
        snapshot = {
            "files": [
                {"path": "Downloads/a.PDF", "hex": "00"},
                {"path": "Downloads/keep.exe", "hex": "01"},
            ],
            "emails": [
                {"id": "m7", "date": "2026-11-03", "subject": "Update", "folder": "INBOX", "sender": "manager", "thread_id": "t7"},
            ],
        }
        files_result = {"moves": [{"from": "Downloads/a.PDF", "to": "Archive/docs/a.PDF"}]}
        mail_result = {"trash_ids": []}
        reply_result = {"email_id": "m7", "thread_id": "t7", "to": "manager", "text": ""}
        contract = {"name": "commit", "inputs": ["a", "b", "c", "d"], "output": "y"}
        result = call_candidate(
            "products/commit/transform.py",
            "transform",
            args=[[snapshot, files_result, mail_result, reply_result], contract],
        )
        paths = [f["path"] for f in result["result"]["files"]]
        self.assertEqual(paths, ["Archive/docs/a.PDF", "Downloads/keep.exe"])

    def test_api_boundaries(self):
        seeds = {
            "products/files/transform.py": {"files": [], "download_prefix": "D", "archive_prefix": "A", "extensions": {}},
            "products/mail/transform.py": {"emails": [], "month": "2026-11", "trash_keyword": "news"},
            "products/reply/transform.py": {"emails": [{"id": "m", "date": "2026-11-03", "subject": "s", "folder": "INBOX", "sender": "m", "thread_id": "t"}], "reply_email_id": "m", "manager": "m", "reply_text": ""},
            "products/commit/transform.py": [
                {"files": [], "emails": []},
                {"moves": []},
                {"trash_ids": []},
                {"email_id": "m", "thread_id": "t", "to": "m", "text": ""},
            ],
        }
        for req in API_BOUNDARY_REQUIREMENTS:
            target = req["target_path"]
            payload = seeds[target]
            contract = {"name": "x", "inputs": ["i"], "output": "o"}
            for rule, spec in req["rules"].items():
                if not spec.get("applicable"):
                    continue
                with self.subTest(target=target, rule=rule):
                    check_api_boundary(
                        target,
                        rule=rule,
                        contract_path=spec["contract_path"],
                        requirement_quote=spec["requirement_quote"],
                        args=[payload, contract],
                    )


if __name__ == "__main__":
    unittest.main()
