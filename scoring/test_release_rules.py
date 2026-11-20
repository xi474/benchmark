import copy
import unittest
from score_attempt import evaluate
from score_run import summarize


class ReleaseRules(unittest.TestCase):
    def setUp(self):
        self.reg={"version":"2.0.0","task":"example","family":"component",
            "empirical_difficulty":"H","reward_difficulty":"M",
            "units":[{"id":k,"group":k,"inputs":v} for k,v in
                     [("A",["api"]),("B",["build1","build2"]),("D",["out"]),("P",["public"])]]}
        self.raw={"task":"example","integrity_ok":True,"checks":[{"id":k,"passed":True}
                  for k in ("api","build1","build2","out","public")]}

    def test_delivery_bonus(self):
        self.assertEqual(evaluate(self.reg,self.raw)["reward"],"2.000000")
        self.raw["checks"][2]["passed"]=False
        r=evaluate(self.reg,self.raw)
        self.assertEqual((r["public_pass"],r["strict_pass"],r["reward"],r["core_transform_case_pass_rate"]),
                         (True,False,"0.750000",1))

    def test_missing_is_not_integrity_failure(self):
        self.assertIsNone(evaluate(self.reg,None)["reward"])
        self.raw["checks"].pop()
        r=evaluate(self.reg,self.raw)
        self.assertEqual((r["total_verifiers"],r["reward"],r["public_pass"]),(4,"0.750000",False))
        self.raw["integrity_ok"]=False
        self.assertEqual(evaluate(self.reg,self.raw)["reward"],"0.000000")

    def test_optional_and_malformed(self):
        self.raw["robustness_all_passed"]=False
        r=evaluate(self.reg,self.raw)
        self.assertEqual((r["strict_pass"],r["full_spec_pass"],r["reward"]),(True,False,"2.000000"))
        self.raw["checks"].append(copy.copy(self.raw["checks"][0]))
        with self.assertRaises(ValueError):
            evaluate(self.reg,self.raw)

    def test_aggregate_retains_missingness(self):
        result=evaluate(self.reg,self.raw)
        missing=dict(evaluate(self.reg,None),task="other")
        catalog=dict(version="2.0.0",scoring_revision=result["scoring_revision"],tasks=[1,2],max_total_reward=4)
        partial=summarize(catalog,[result,missing])
        self.assertEqual((partial["reward_total"],partial["reward_sum_on_scored"],partial["unknown_ids"]),
                         (None,"2.000000",["other"]))
        full=summarize(catalog,[result,dict(result,task="other")])
        self.assertEqual((full["strict_pass_rate"],full["reward_total"]),(1,"4.000000"))
