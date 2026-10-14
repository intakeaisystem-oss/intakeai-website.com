import json
import unittest
from pathlib import Path

from marketing_toolkit import psychology, text, voc

SAMPLE = json.loads((Path(__file__).resolve().parent.parent / "examples" / "marketing" / "sample_inputs.json").read_text())
DOCS = SAMPLE["documents"]


class VocTests(unittest.TestCase):
    def setUp(self):
        self.r = voc.analyze(DOCS, competitors=["BigFSM"])

    def test_quotes_are_verbatim_substrings(self):
        texts = {d["id"]: d["text"] for d in DOCS}
        n = 0
        for cat in self.r["categories"].values():
            for th in cat["themes"]:
                self.assertTrue(th["label_is_generated"])
                for q in th["quotes"]:
                    self.assertTrue(q["verbatim"])
                    self.assertIn(q["quote"], texts[q["doc_id"]])
                    n += 1
        self.assertGreater(n, 5)

    def test_categories_detected(self):
        c = self.r["categories"]
        for cat in ("problem", "desired_outcome", "objection", "product_complaint", "abandonment_reason", "purchase_trigger"):
            self.assertGreater(c[cat]["document_count"], 0, cat)

    def test_competitor_mentions(self):
        cm = self.r["competitor_mentions"][0]
        self.assertEqual(cm["competitor"], "BigFSM")
        self.assertGreaterEqual(cm["negative_context_count"], 1)

    def test_near_duplicate_removed(self):
        docs = DOCS + [{"id": "dup", "text": DOCS[0]["text"] + " ", "source_type": "review"}]
        r = voc.analyze(docs)
        self.assertIn("dup", r["near_duplicates_removed"])

    def test_quote_permission_respected(self):
        r = voc.analyze([{"id": "a", "text": "Scheduling is so frustrating and takes forever.", "quote_permitted": False}])
        q = r["categories"]["problem"]["themes"][0]["quotes"][0]
        self.assertFalse(q["verbatim"])
        self.assertIn("withheld", q["quote"])

    def test_limitations_flag_small_sample(self):
        self.assertTrue(any("indicative" in x for x in self.r["limitations"]))

    def test_empty_input(self):
        with self.assertRaises(ValueError):
            voc.analyze([])

    def test_to_records_validate(self):
        from marketing_toolkit.store import KnowledgeStore
        s = KnowledgeStore()
        many = DOCS * 1 + [{"id": f"x{i}", "text": f"Scheduling takes hours every week, case {i}.", "source_type": "survey"} for i in range(4)]
        for r in voc.to_records(voc.analyze(many), "P"):
            s.add(r, on_conflict="version")
        self.assertGreater(s.stats()["total"], 0)


class TextTests(unittest.TestCase):
    def test_readability(self):
        r = text.readability("The cat sat on the mat. It was happy.")
        self.assertGreater(r["flesch"], 80)

    def test_cluster(self):
        groups = text.cluster(["price is too high", "too high a price", "support was slow", "slow support team"], 0.3)
        self.assertEqual(len(groups), 2)

    def test_similarity_bounds(self):
        self.assertAlmostEqual(text.similarity("abc def", "abc def"), 1.0, places=5)
        self.assertEqual(text.similarity("apples oranges", "trucks engines"), 0.0)


class ProfileTests(unittest.TestCase):
    def test_profile_structure_and_labels(self):
        p = psychology.build_profile(SAMPLE["product"], "owners", DOCS)
        for key in ("jobs_to_be_done", "pain_points", "desired_outcomes", "purchase_triggers", "buy_now_vs_later",
                    "existing_alternatives", "reasons_for_distrust", "objections", "dimensions", "messaging_implications",
                    "validation_plan"):
            self.assertIn(key, p)
        self.assertEqual(len(p["dimensions"]), 21)
        for ins in p["pain_points"]:
            self.assertEqual(ins["basis"], "observed")
            self.assertTrue(ins["evidence"])
        self.assertTrue(any('"' in i["implication"] for i in p["messaging_implications"]))  # uses real quotes

    def test_no_evidence_means_hypothesis(self):
        p = psychology.build_profile({"name": "X", "description": "a tool"}, "anyone")
        self.assertEqual(p["jobs_to_be_done"][0]["basis"], "hypothesis")
        self.assertEqual(p["purchase_triggers"][0]["basis"], "hypothesis")
        self.assertTrue(all(v["basis"] == "hypothesis" for k, v in p["dimensions"].items()))
        self.assertTrue(p["validation_plan"])
        self.assertIn("collect VoC", p["messaging_implications"][0]["implication"])

    def test_stated_vs_observed(self):
        p = psychology.build_profile({"name": "X"}, "", DOCS, stated_vs_observed=[
            {"stated": "price matters most", "observed": "buyers chose the most expensive plan", "source": "analytics"}])
        self.assertEqual(p["dimensions"]["stated_vs_observed"]["basis"], "measured")

    def test_to_records(self):
        from marketing_toolkit.store import KnowledgeStore
        s = KnowledgeStore()
        for r in psychology.to_records(psychology.build_profile(SAMPLE["product"], "owners", DOCS), "P"):
            s.add(r, on_conflict="version")
        self.assertEqual(len(s.find(kind="customer_profile")), 1)


if __name__ == "__main__":
    unittest.main()


class DeterminismTests(unittest.TestCase):
    def test_same_output_across_hash_seeds(self):
        import os
        import subprocess
        import sys
        root = Path(__file__).resolve().parent.parent
        code = ("import json; from marketing_toolkit import voc, psychology; "
                "d = json.load(open('examples/marketing/sample_inputs.json')); "
                "v = voc.analyze(d['documents'], competitors=['BigFSM']); "
                "p = psychology.build_profile(d['product'], 'o', d['documents'], v); "
                "print(json.dumps([v, p], sort_keys=True))")
        outs = []
        for seed in ("1", "99"):
            env = dict(os.environ, PYTHONHASHSEED=seed, PYTHONPATH=str(root))
            r = subprocess.run([sys.executable, "-c", code], cwd=root, capture_output=True, text=True, env=env, timeout=60)
            self.assertEqual(r.returncode, 0, r.stderr)
            outs.append(r.stdout)
        self.assertEqual(outs[0], outs[1])
