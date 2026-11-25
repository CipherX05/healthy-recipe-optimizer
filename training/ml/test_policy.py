import json
import tempfile
import unittest
from pathlib import Path
from policy import build_case, choose_teacher, make_dataset, parse_selection, read_jsonl, summarize

class PolicyTests(unittest.TestCase):
    def test_ineligible_top_candidate_cannot_block_improvement(self):
        case=build_case("butter-chicken","butter","satFat")
        by_id={x["id"]:x for x in case["candidates"]}
        self.assertFalse(by_id["ghee"]["eligible"])
        self.assertTrue(by_id[case["target"]]["eligible"])

    def test_zero_fiber_can_improve(self):
        case=build_case("butter-chicken","cream","fiber")
        self.assertTrue(any(x["eligible"] for x in case["candidates"]))
        self.assertIsNotNone(case["target"])
        self.assertTrue(all(0<=x["N"]<=1 for x in case["candidates"]))

    def test_null_only_when_no_eligible_candidate(self):
        c=build_case("mapo-tofu","chiliOil","protein")
        self.assertIsNone(c["target"])
        self.assertTrue(parse_selection('{"candidate_id":null}',c["candidates"])["eligible"])
        c=build_case("butter-chicken","cream","satFat")
        self.assertFalse(parse_selection('{"candidate_id":null}',c["candidates"])["eligible"])

    def test_strict_outputs_and_invalid_candidates(self):
        case=build_case("butter-chicken","cream","satFat")
        for output in ["prose",'{"candidate_id":"unknown"}','{"candidate_id":[]}',
                       '{"candidate_id":{},"extra":1}','[]','{"candidate_id":"cashewCream","extra":1}']:
            self.assertFalse(parse_selection(output,case["candidates"])["candidate_valid"])
        self.assertTrue(parse_selection(case["completion"],case["candidates"])["eligible"])

    def test_shuffle_preserves_rule_target(self):
        a=build_case("butter-chicken","cream","satFat")
        for i in range(12):
            b=build_case("butter-chicken","cream","satFat",i)
            self.assertEqual(a["target"],b["target"])

    def test_split_family_isolation_and_provenance(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest=make_dataset(directory)
            groups=[]
            for split in ["train","validation","test"]:
                rows=read_jsonl(Path(directory)/f"{split}.jsonl")
                groups.append({r["recipe_family"] for r in rows})
                self.assertTrue(all(r["review_status"]=="unreviewed" for r in rows))
                self.assertTrue(all(r["target"]==choose_teacher(r["candidates"]) for r in rows))
                self.assertTrue(all("pecorino" not in {c["id"] for c in r["candidates"]} for r in rows))
            for i in range(3):
                for j in range(i):self.assertTrue(groups[i].isdisjoint(groups[j]))
            self.assertEqual(manifest["splits"]["test"]["independent_queries"],8)
            self.assertEqual(manifest["splits"]["train"]["independent_queries"],28)

    def test_metrics_do_not_hide_invalid_model_outputs(self):
        rows=[{"query_id":"q","recipe_family":"r","target":"ok","selected":None,
               "candidate_valid":False,"json_valid":False,"eligible":False}]
        self.assertEqual(summarize(rows)["rule_agreement"],0)

if __name__=="__main__":unittest.main()
