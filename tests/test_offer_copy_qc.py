import copy as _copy
import json
import unittest
from pathlib import Path

from marketing_toolkit import copywriting as cw
from marketing_toolkit import offer, qc

SAMPLE = json.loads((Path(__file__).resolve().parent.parent / "examples" / "marketing" / "sample_inputs.json").read_text())
OFFER = SAMPLE["offer"]


class OfferTests(unittest.TestCase):
    def test_score_and_blockers(self):
        r = offer.score_offer(OFFER)
        self.assertEqual(len(r["criteria"]), 15)
        self.assertIn("proof", r["blockers"])
        self.assertFalse(r["passed"])
        self.assertTrue(r["top_improvements"])
        self.assertEqual(r["economics"]["gross_profit_per_purchase"], 67)

    def test_verified_proof_and_real_urgency(self):
        o = _copy.deepcopy(OFFER)
        o["proof"] = [{"type": "review_rating", "verified": True}, {"type": "case_study", "verified": True},
                      {"type": "demo", "verified": True}]
        o["urgency_reason"], o["urgency_is_real"] = "price rises on 1 Jan (announced)", True
        o["risk_reversal"], o["guarantee_terms_verified"] = "30-day refund", True
        r = offer.score_offer(o)
        self.assertEqual(r["blockers"], [])
        self.assertTrue(r["passed"])

    def test_fake_urgency_and_unverified_proof_block(self):
        o = _copy.deepcopy(OFFER)
        o["urgency_reason"] = "only 3 spots left"
        o["proof"] = [{"type": "testimonial", "verified": False}]
        r = offer.score_offer(o)
        self.assertIn("urgency", r["blockers"])
        self.assertTrue(any("unverified" in i for c in r["criteria"] for i in c["issues"]))

    def test_hype_and_generic_audience(self):
        o = {"name": "X", "target_customer": "everyone", "value_proposition": "Revolutionary game-changing platform"}
        r = offer.score_offer(o)
        crit = {c["criterion"]: c for c in r["criteria"]}
        self.assertLessEqual(crit["target_customer"]["score"], 2)
        self.assertTrue(any("hype" in i.lower() for i in crit["value_proposition"]["issues"]))

    def test_negative_margin(self):
        o = dict(OFFER, fulfillment_cost=100)
        crit = {c["criterion"]: c for c in offer.score_offer(o)["criteria"]}
        self.assertEqual(crit["economics"]["score"], 0)

    def test_weights_configurable(self):
        base = offer.score_offer(OFFER)["overall"]
        heavy = offer.score_offer(OFFER, {"offer_weights": {"proof": 20}})["overall"]
        self.assertLess(heavy, base)

    def test_structures_use_placeholders_not_inventions(self):
        g = offer.generate_structures({"name": "X"})
        self.assertEqual(len(g["structures"]), 6)
        self.assertIn("[SET PRICE]", g["structures"][0]["shape"])
        self.assertEqual(len(g["awareness_angles"]), 5)


class QcTests(unittest.TestCase):
    def codes(self, text, ctx=None):
        return {f["code"] for f in qc.evaluate(text, ctx)["findings"]}

    def test_detects_each_problem(self):
        self.assertIn("unsupported_claim", self.codes("Increase revenue by 300%. Book a demo."))
        self.assertIn("unsupported_claim", self.codes("The #1 scheduling app. Try it."))
        self.assertIn("fabricated_testimonial", self.codes('"This changed my life completely" - Sarah. Sign up.'))
        self.assertIn("misleading_scarcity", self.codes("Only 3 spots left! Join now."))
        self.assertIn("unrealistic_promise", self.codes("Guaranteed results overnight. Start now."))
        self.assertIn("policy_risk_high", self.codes("Are you overweight? Try our plan."))
        self.assertIn("generic_messaging", self.codes("We help businesses take your business to the next level. Contact us."))
        self.assertIn("unclear_cta", self.codes("Our scheduling tool has a calendar view."))
        self.assertIn("missing_proof", self.codes("Schedule jobs faster. Start a trial.", {"kind": "ad"}))
        self.assertIn("missing_measurement_plan", self.codes("Start a trial.", {"require_measurement": True}))

    def test_substantiated_claims_pass(self):
        t = "Rated 4.8/5 by 120 owners. Start a trial."
        self.assertIn("unsupported_claim", self.codes(t))
        self.assertNotIn("unsupported_claim", self.codes(t, {"substantiated_claims": ["Rated 4.8/5 by 120 owners"]}))

    def test_real_urgency_allowed(self):
        self.assertNotIn("misleading_scarcity", self.codes("Limited time: ends Friday. Book now.", {"urgency_is_real": True}))

    def test_message_mismatch_and_repeats(self):
        f = self.codes("Schedule HVAC techs in 10 minutes. Try free.", {"landing_text": "Accounting software for law firms"})
        self.assertIn("message_mismatch", f)
        f2 = self.codes("Schedule your techs in minutes. Try it.", {"other_concepts": ["Schedule your techs in minutes. Try it now."]})
        self.assertIn("repeated_concept", f2)

    def test_decision(self):
        self.assertEqual(qc.evaluate("Only 2 left! 10x your sales overnight.")["decision"], "reject")
        good = qc.evaluate("Schedule a week of jobs in one screen, unlike spreadsheets. See reviews from customers. Start a 14-day trial.",
                           {"kind": "landing"})
        self.assertEqual(good["decision"], "approve")


class CopyTests(unittest.TestCase):
    def test_evaluate_good_copy(self):
        r = cw.evaluate_copy({"text": SAMPLE["copy"], "offer": OFFER, "audience_terms": ["techs", "scheduling"], "kind": "landing"})
        self.assertEqual(len(r["criteria"]), 12)
        self.assertTrue(r["passed"], r["priority_fixes"])

    def test_weak_copy_explains_fixes(self):
        r = cw.evaluate_copy({"text": "We are a leading innovative solution that leverages synergy for businesses.",
                              "audience_terms": ["techs"], "known_objections": ["too expensive"]})
        self.assertFalse(r["passed"])
        self.assertTrue(all(f["fix"] for f in r["priority_fixes"]))
        self.assertGreaterEqual(len(r["priority_fixes"]), 3)

    def test_offer_consistency(self):
        r = cw.evaluate_copy({"text": "Get it for $49/month. Start now.", "offer": OFFER})
        crit = {c["criterion"]: c for c in r["criteria"]}
        self.assertLess(crit["offer_consistency"]["score"], 3)

    def test_channel_limits(self):
        r = cw.evaluate_copy({"text": "Schedule every technician in minutes today", "channel": "google_rsa_headline"})
        self.assertTrue(r["channel_issues"])
        self.assertFalse(r["passed"])

    def test_draft_placeholders(self):
        d = cw.build_draft("pas", {"offer": OFFER, "pains": ["Scheduling takes hours"], "proof": [{"text": "fake", "verified": False}]})
        self.assertEqual([s["section"] for s in d["sections"]], ["problem", "agitation", "solution", "proof", "cta"])
        self.assertIn("VERIFIED PROOF", d["sections"][3]["draft"])  # unverified proof never used
        for fw in cw.FRAMEWORKS:
            self.assertTrue(cw.build_draft(fw, {})["sections"])
        with self.assertRaises(ValueError):
            cw.build_draft("nope", {})

    def test_recommend_framework(self):
        self.assertIn("pas", cw.recommend_framework("problem_aware"))
        self.assertEqual(cw.recommend_framework(None, "video_ad_script")[0], "demonstration")


if __name__ == "__main__":
    unittest.main()
