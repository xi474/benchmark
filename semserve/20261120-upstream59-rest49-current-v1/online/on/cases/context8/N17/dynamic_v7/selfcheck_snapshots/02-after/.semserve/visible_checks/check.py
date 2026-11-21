import unittest

API_BOUNDARY_REQUIREMENTS = [
    {
        "target_path": "engines/template_dependencies/engine.py",
        "function": "transform",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": False,
                "contract_path": "engines/template_dependencies/SPEC.md",
                "requirement_quote": "仅考查公开合法输入域与明确业务拒绝分支，不要求任意畸形输入、额外字段递归检查、异常文案或隐藏兼容行为。",
                "reason": "SPEC explicitly excludes arbitrary malformed input and extra-field recursion checks.",
            },
            "invalid_payload_type": {
                "applicable": False,
                "contract_path": "engines/template_dependencies/SPEC.md",
                "requirement_quote": "仅考查公开合法输入域与明确业务拒绝分支，不要求任意畸形输入、额外字段递归检查、异常文案或隐藏兼容行为。",
                "reason": "SPEC excludes arbitrary malformed input; no ValueError rule is documented.",
            },
        },
    },
    {
        "target_path": "engines/stylesheet_updates/engine.py",
        "function": "transform",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": False,
                "contract_path": "engines/stylesheet_updates/SPEC.md",
                "requirement_quote": "仅考查公开合法输入域与明确业务拒绝分支，不要求任意畸形输入、额外字段递归检查、异常文案或隐藏兼容行为。",
                "reason": "SPEC excludes arbitrary malformed input and extra-field recursion checks.",
            },
            "invalid_payload_type": {
                "applicable": False,
                "contract_path": "engines/stylesheet_updates/SPEC.md",
                "requirement_quote": "仅考查公开合法输入域与明确业务拒绝分支，不要求任意畸形输入、额外字段递归检查、异常文案或隐藏兼容行为。",
                "reason": "SPEC excludes arbitrary malformed input; no ValueError rule is documented.",
            },
        },
    },
    {
        "target_path": "engines/reverse_index/engine.py",
        "function": "transform",
        "rules": {
            "nonfinite_unknown_field": {
                "applicable": False,
                "contract_path": "engines/reverse_index/SPEC.md",
                "requirement_quote": "仅考查公开合法输入域与明确业务拒绝分支，不要求任意畸形输入、额外字段递归检查、异常文案或隐藏兼容行为。",
                "reason": "SPEC excludes arbitrary malformed input and extra-field recursion checks.",
            },
            "invalid_payload_type": {
                "applicable": False,
                "contract_path": "engines/reverse_index/SPEC.md",
                "requirement_quote": "仅考查公开合法输入域与明确业务拒绝分支，不要求任意畸形输入、额外字段递归检查、异常文案或隐藏兼容行为。",
                "reason": "SPEC excludes arbitrary malformed input; no ValueError rule is documented.",
            },
        },
    },
]


class TestTemplateDependencies(unittest.TestCase):
    def test_longest_prefix_and_subscript_to_dot(self):
        # conf.aliases['a'].propname -> aliases (longest legal prefix)
        payload = {
            "templates": {
                "a": "{{ conf.auto_save.interval + conf.hints.min_chars }}",
                "b": "{{ conf.aliases['a'].propname }} {{ notconf.hints.min_chars }}",
            },
            "options": ["auto_save.interval", "hints.min_chars", "aliases"],
        }
        expected = {
            "a": ["auto_save.interval", "hints.min_chars"],
            "b": ["aliases"],
        }
        result = call_candidate(
            "engines/template_dependencies/engine.py", "transform",
            args=[payload, None],
        )
        self.assertEqual(result, expected)

    def test_ignores_notconf_and_plain_text(self):
        payload = {
            "templates": {
                "x": "plain text {{ notconf.a.b }} {{ conf.hints.min_chars }}",
            },
            "options": ["hints.min_chars", "hints"],
        }
        result = call_candidate(
            "engines/template_dependencies/engine.py", "transform",
            args=[payload, None],
        )
        self.assertEqual(result, {"x": ["hints.min_chars"]})


class TestStylesheetUpdates(unittest.TestCase):
    def test_affected_intersection_sorted(self):
        payload = {
            "dependencies": {
                "b": ["aliases"],
                "a": ["auto_save.interval", "hints.min_chars"],
            },
            "changed": ["hints.min_chars"],
        }
        result = call_candidate(
            "engines/stylesheet_updates/engine.py", "transform",
            args=[payload, None],
        )
        self.assertEqual(result["dependencies"], payload["dependencies"])
        self.assertEqual(result["affected"], ["a"])

    def test_no_affected(self):
        payload = {
            "dependencies": {"a": ["auto_save.interval"]},
            "changed": ["hints.min_chars"],
        }
        result = call_candidate(
            "engines/stylesheet_updates/engine.py", "transform",
            args=[payload, None],
        )
        self.assertEqual(result["affected"], [])


class TestReverseIndex(unittest.TestCase):
    def test_reverse_index_sorted(self):
        payload = {
            "dependencies": {
                "b": ["aliases"],
                "a": ["auto_save.interval", "hints.min_chars"],
            },
        }
        result = call_candidate(
            "engines/reverse_index/engine.py", "transform",
            args=[payload, None],
        )
        self.assertEqual(
            result,
            {
                "aliases": ["b"],
                "auto_save.interval": ["a"],
                "hints.min_chars": ["a"],
            },
        )


if __name__ == "__main__":
    unittest.main()
