import unittest

# Injected names (no import needed).
# call_candidate(path, function, args=[...]) -> JSON value
# check_api_boundary(...) -> raises on failure
# CandidateCallError -> exception with details dict

CHAIN_PAYLOAD = {
    "root": "a",
    "nodes": [
        {"id": "a", "type": "T", "message": "m", "cause": None,
         "context": None, "suppress_context": False, "frames": []},
    ],
}
CHAIN_CONTRACT = {"name": "chain", "operation": "exception_chain",
                  "inputs": ["inputs/case.json"], "output": "outputs/chain.json"}
FRAMES_CONTRACT = {"name": "frames", "operation": "portable_frames",
                   "inputs": ["inputs/case.json"], "output": "outputs/frames.json"}
REPORT_CONTRACT = {"name": "report", "operation": "exception_report",
                   "inputs": ["outputs/chain.json", "outputs/frames.json"],
                   "output": "outputs/report.json"}

API_BOUNDARY_REQUIREMENTS = [
    {
        "target_path": "chain/transform.py",
        "function": "transform",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": True,
                "contract_path": "README.md",
                "requirement_quote": "未知额外字段可忽略，但其中非有限JSON仍非法",
                "args": [[CHAIN_PAYLOAD], CHAIN_CONTRACT],
            },
            "invalid_payload_type": {
                "applicable": True,
                "contract_path": "README.md",
                "requirement_quote": "仅对象/数组顶层合法；非法JSON、其他顶层类型和任意嵌套NaN/Infinity抛ValueError",
                "args": [[CHAIN_PAYLOAD], CHAIN_CONTRACT],
            },
        },
    },
    {
        "target_path": "frames/transform.py",
        "function": "transform",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": True,
                "contract_path": "README.md",
                "requirement_quote": "未知额外字段可忽略，但其中非有限JSON仍非法",
                "args": [[CHAIN_PAYLOAD], FRAMES_CONTRACT],
            },
            "invalid_payload_type": {
                "applicable": True,
                "contract_path": "README.md",
                "requirement_quote": "仅对象/数组顶层合法；非法JSON、其他顶层类型和任意嵌套NaN/Infinity抛ValueError",
                "args": [[CHAIN_PAYLOAD], FRAMES_CONTRACT],
            },
        },
    },
    {
        "target_path": "report/transform.py",
        "function": "transform",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": True,
                "contract_path": "README.md",
                "requirement_quote": "未知额外字段可忽略，但其中非有限JSON仍非法",
                "args": [[{"chain": []}, {"frames": {}}], REPORT_CONTRACT],
            },
            "invalid_payload_type": {
                "applicable": True,
                "contract_path": "README.md",
                "requirement_quote": "仅对象/数组顶层合法；非法JSON、其他顶层类型和任意嵌套NaN/Infinity抛ValueError",
                "args": [[{"chain": []}, {"frames": {}}], REPORT_CONTRACT],
            },
        },
    },
]


class TestApiBoundaries(unittest.TestCase):
    def test_api_boundary_rules(self):
        for entry in API_BOUNDARY_REQUIREMENTS:
            target = entry["target_path"]
            for rule, spec in entry["rules"].items():
                with self.subTest(target=target, rule=rule):
                    if not spec["applicable"]:
                        continue
                    check_api_boundary(
                        target,
                        rule=rule,
                        contract_path=spec["contract_path"],
                        requirement_quote=spec["requirement_quote"],
                        args=spec.get("args"),
                    )


class TestChainBehavior(unittest.TestCase):
    def test_chain_cycle_raises(self):
        payload = {
            "root": "a",
            "nodes": [
                {"id": "a", "type": "T", "message": "m", "cause": "b",
                 "context": None, "suppress_context": False, "frames": []},
                {"id": "b", "type": "T", "message": "m", "cause": "a",
                 "context": None, "suppress_context": False, "frames": []},
            ],
        }
        with self.assertRaises(CandidateCallError) as cm:
            call_candidate("chain/transform.py", "transform",
                           args=[[payload], CHAIN_CONTRACT])
        self.assertEqual(cm.exception.details["failure_phase"], "candidate_exception")
        self.assertEqual(cm.exception.details["error_type"], "ValueError")

    def test_chain_suppressed_context_not_followed(self):
        payload = {
            "root": "a",
            "nodes": [
                {"id": "a", "type": "T", "message": "m", "cause": None,
                 "context": "b", "suppress_context": True, "frames": []},
                {"id": "b", "type": "T", "message": "m", "cause": None,
                 "context": None, "suppress_context": False, "frames": []},
            ],
        }
        result = call_candidate("chain/transform.py", "transform",
                                args=[[payload], CHAIN_CONTRACT])
        self.assertEqual(result["name"], "chain")
        self.assertEqual(result["result"]["chain"],
                         [{"id": "a", "type": "T", "message": "m", "link": None}])


class TestFramesBehavior(unittest.TestCase):
    def test_frames_basename_and_locals(self):
        payload = {
            "root": "a",
            "nodes": [
                {"id": "a", "type": "T", "message": "m", "cause": None,
                 "context": None, "suppress_context": False,
                 "frames": [
                     {"file": "C:\\dir\\mod.py", "line": 5, "function": "f",
                      "locals": {"b": True, "a": 1}},
                 ]},
            ],
        }
        result = call_candidate("frames/transform.py", "transform",
                                args=[[payload], FRAMES_CONTRACT])
        frames = result["result"]["frames"]["a"]
        self.assertEqual(frames[0]["file"], "mod.py")
        self.assertEqual(frames[0]["locals"], {"a": "1", "b": "true"})


class TestReportBehavior(unittest.TestCase):
    def test_report_text_and_nodes(self):
        chain = {"name": "chain", "result": {"chain": [
            {"id": "inner", "type": "KeyError", "message": "k", "link": None},
            {"id": "outer", "type": "RuntimeError", "message": "f", "link": "cause"},
        ]}}
        frames = {"name": "frames", "result": {"frames": {
            "inner": [{"file": "m.py", "line": 3, "function": "lookup",
                       "locals": {"key": '"x"'}}],
            "outer": [{"file": "a.py", "line": 8, "function": "run",
                       "locals": {"data": "[1,true,null]"}}],
        }}}
        result = call_candidate("report/transform.py", "transform",
                                args=[[chain, frames], REPORT_CONTRACT])
        self.assertEqual(result["result"]["text"],
                         "  m.py:3 in lookup\nKeyError: k\n"
                         "--- direct cause ---\n  a.py:8 in run\nRuntimeError: f\n")
        self.assertEqual(len(result["result"]["nodes"]), 2)
        self.assertEqual(result["result"]["nodes"][1]["link"], "cause")


if __name__ == "__main__":
    unittest.main()
