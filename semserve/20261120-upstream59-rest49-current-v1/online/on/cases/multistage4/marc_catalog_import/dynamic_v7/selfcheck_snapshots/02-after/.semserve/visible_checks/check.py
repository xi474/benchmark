import unittest

API_BOUNDARY_REQUIREMENTS = [
    {
        "target_path": "domains/reader/transform.py",
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
        "target_path": "domains/names/transform.py",
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
        "target_path": "domains/languages/transform.py",
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
        "target_path": "domains/subjects/transform.py",
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
        "target_path": "views/catalog/transform.py",
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


class TestReaderTransform(unittest.TestCase):
    def test_reader_parses_records(self):
        xml = (
            '<collection xmlns="http://www.loc.gov/MARC21/slim">'
            '<record><controlfield tag="001">b1</controlfield>'
            '<controlfield tag="008">' + " " * 35 + "eng  " + '</controlfield>'
            '<datafield tag="100"><subfield code="a">A</subfield></datafield>'
            '</record></collection>'
        )
        payload = {"xml": xml, "language_codes": ["eng"]}
        contract = {"name": "reader", "operation": "marc_xml_records",
                    "inputs": ["inputs/case.json"], "output": "outputs/reader.json"}
        result = call_candidate("domains/reader/transform.py", "transform",
                                args=[[payload], contract])
        self.assertEqual(result["name"], "reader")
        self.assertEqual(len(result["result"]["records"]), 1)
        rec = result["result"]["records"][0]
        self.assertEqual(rec["id"], "b1")
        self.assertEqual(rec["controls"]["001"], "b1")
        self.assertEqual(rec["fields"][0]["tag"], "100")

    def test_reader_rejects_doctype(self):
        xml = '<!DOCTYPE collection><collection><record><controlfield tag="001">b1</controlfield></record></collection>'
        payload = {"xml": xml, "language_codes": ["eng"]}
        contract = {"name": "reader", "operation": "marc_xml_records",
                    "inputs": ["inputs/case.json"], "output": "outputs/reader.json"}
        with self.assertRaises(CandidateCallError) as cm:
            call_candidate("domains/reader/transform.py", "transform",
                           args=[[payload], contract])
        self.assertEqual(cm.exception.details["failure_phase"], "candidate_exception")
        self.assertEqual(cm.exception.details["error_type"], "ValueError")


class TestLanguagesTransform(unittest.TestCase):
    def test_languages_gerlat_split(self):
        raw = {"language_codes": ["eng", "ger", "lat"]}
        records = [{"id": "b1",
                    "controls": {"008": " " * 35 + "eng  "},
                    "fields": [{"tag": "041", "subfields": [{"code": "a", "value": "gerlat"}]}]}]
        contract = {"name": "languages", "operation": "marc_languages",
                    "inputs": ["inputs/case.json", "outputs/reader.json"],
                    "output": "outputs/languages.json"}
        result = call_candidate("domains/languages/transform.py", "transform",
                                args=[[raw, {"records": records}], contract])
        self.assertEqual(result["result"]["records"][0]["languages"],
                         ["eng", "ger", "lat"])

    def test_languages_bad_length(self):
        raw = {"language_codes": ["eng"]}
        records = [{"id": "b1",
                    "controls": {},
                    "fields": [{"tag": "041", "subfields": [{"code": "a", "value": "engx"}]}]}]
        contract = {"name": "languages", "operation": "marc_languages",
                    "inputs": ["inputs/case.json", "outputs/reader.json"],
                    "output": "outputs/languages.json"}
        with self.assertRaises(CandidateCallError) as cm:
            call_candidate("domains/languages/transform.py", "transform",
                           args=[[raw, {"records": records}], contract])
        self.assertEqual(cm.exception.details["failure_phase"], "candidate_exception")
        self.assertEqual(cm.exception.details["error_type"], "ValueError")


class TestSubjectsTransform(unittest.TestCase):
    def test_subjects_count(self):
        records = [{"id": "b1", "fields": [
            {"tag": "610", "subfields": [{"code": "a", "value": "Jesuits."},
                                         {"code": "b", "value": "Dept."}]},
            {"tag": "610", "subfields": [{"code": "a", "value": "Jesuits."},
                                         {"code": "b", "value": "Dept."}]},
        ]}]
        contract = {"name": "subjects", "operation": "marc_subjects",
                    "inputs": ["outputs/reader.json"], "output": "outputs/subjects.json"}
        result = call_candidate("domains/subjects/transform.py", "transform",
                                args=[[{"records": records}], contract])
        orgs = result["result"]["records"][0]["subjects"]["organizations"]
        self.assertEqual(orgs, [{"value": "Jesuits. Dept.", "count": 2}])


class TestCatalogTransform(unittest.TestCase):
    def test_catalog_join(self):
        names = {"records": [{"id": "b1", "authors": [], "titles": []}]}
        langs = {"records": [{"id": "b1", "languages": ["eng"]}]}
        subs = {"records": [{"id": "b1", "subjects": {}}]}
        contract = {"name": "catalog", "operation": "marc_catalog",
                    "inputs": ["outputs/names.json", "outputs/languages.json",
                               "outputs/subjects.json"],
                    "output": "outputs/catalog.json"}
        result = call_candidate("views/catalog/transform.py", "transform",
                                args=[[names, langs, subs], contract])
        self.assertEqual(result["result"]["record_count"], 1)
        self.assertEqual(result["result"]["records"][0]["id"], "b1")
        self.assertEqual(result["result"]["records"][0]["languages"], ["eng"])

    def test_catalog_mismatch_ids(self):
        names = {"records": [{"id": "b1", "authors": [], "titles": []}]}
        langs = {"records": [{"id": "b2", "languages": ["eng"]}]}
        subs = {"records": [{"id": "b1", "subjects": {}}]}
        contract = {"name": "catalog", "operation": "marc_catalog",
                    "inputs": ["outputs/names.json", "outputs/languages.json",
                               "outputs/subjects.json"],
                    "output": "outputs/catalog.json"}
        with self.assertRaises(CandidateCallError) as cm:
            call_candidate("views/catalog/transform.py", "transform",
                           args=[[names, langs, subs], contract])
        self.assertEqual(cm.exception.details["failure_phase"], "candidate_exception")
        self.assertEqual(cm.exception.details["error_type"], "ValueError")


if __name__ == "__main__":
    unittest.main()


class TestAPIBoundary(unittest.TestCase):
    def test_api_boundary_probes(self):
        reader_contract = {"name": "reader", "operation": "marc_xml_records",
                           "inputs": ["inputs/case.json"], "output": "outputs/reader.json"}
        names_contract = {"name": "names", "operation": "marc_names_titles",
                          "inputs": ["outputs/reader.json"], "output": "outputs/names.json"}
        langs_contract = {"name": "languages", "operation": "marc_languages",
                          "inputs": ["inputs/case.json", "outputs/reader.json"],
                          "output": "outputs/languages.json"}
        subs_contract = {"name": "subjects", "operation": "marc_subjects",
                         "inputs": ["outputs/reader.json"], "output": "outputs/subjects.json"}
        cat_contract = {"name": "catalog", "operation": "marc_catalog",
                        "inputs": ["outputs/names.json", "outputs/languages.json",
                                   "outputs/subjects.json"],
                        "output": "outputs/catalog.json"}

        reader_payload = {"xml": "<collection><record><controlfield tag=\"001\">b1</controlfield></record></collection>",
                          "language_codes": ["eng"]}
        names_payload = {"records": [{"id": "b1", "authors": [], "titles": []}]}
        langs_raw = {"language_codes": ["eng"]}
        langs_records = {"records": [{"id": "b1", "controls": {}, "fields": []}]}
        subs_payload = {"records": [{"id": "b1", "fields": []}]}
        cat_names = {"records": [{"id": "b1", "authors": [], "titles": []}]}
        cat_langs = {"records": [{"id": "b1", "languages": []}]}
        cat_subs = {"records": [{"id": "b1", "subjects": {}}]}

        probes = [
            ("domains/reader/transform.py", "invalid_payload_type", [reader_payload], reader_contract),
            ("domains/reader/transform.py", "nonfinite_unknown_field", [reader_payload], reader_contract),
            ("domains/names/transform.py", "invalid_payload_type", [names_payload], names_contract),
            ("domains/names/transform.py", "nonfinite_unknown_field", [names_payload], names_contract),
            ("domains/languages/transform.py", "invalid_payload_type", [langs_raw, langs_records], langs_contract),
            ("domains/languages/transform.py", "nonfinite_unknown_field", [langs_raw, langs_records], langs_contract),
            ("domains/subjects/transform.py", "invalid_payload_type", [subs_payload], subs_contract),
            ("domains/subjects/transform.py", "nonfinite_unknown_field", [subs_payload], subs_contract),
            ("views/catalog/transform.py", "invalid_payload_type", [cat_names, cat_langs, cat_subs], cat_contract),
            ("views/catalog/transform.py", "nonfinite_unknown_field", [cat_names, cat_langs, cat_subs], cat_contract),
        ]
        for target, rule, args, contract in probes:
            with self.subTest(target=target, rule=rule):
                check_api_boundary(target, rule=rule, contract_path="README.md",
                                   requirement_quote="未知额外字段可忽略，但其中非有限JSON仍非法。",
                                   args=args)
