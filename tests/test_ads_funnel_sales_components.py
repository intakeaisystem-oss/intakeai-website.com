import json
import unittest
from pathlib import Path

from marketing_toolkit import ads, components, funnel, sales
from marketing_toolkit.store import KnowledgeStore

ROOT = Path(__file__).resolve().parent.parent
SAMPLE = json.loads((ROOT / "examples" / "marketing" / "sample_inputs.json").read_text())
HTML = (ROOT / "examples" / "marketing" / "sample_landing.html").read_text()
BRIEF = {"offer": SAMPLE["offer"], "pains": ["Scheduling takes hours every week."], "outcomes": [SAMPLE["offer"]["desired_outcome"]],
         "objections": ["too expensive for a small shop"], "audience": "small HVAC owners", "job": "schedule a week of jobs",
         "cta": "Start free trial", "objective": "leads"}


class AdsTests(unittest.TestCase):
    def test_ten_distinct_angles(self):
        g = ads.generate_concepts(BRIEF)
        self.assertEqual(len(g["concepts"]), 10)
        self.assertEqual(len({c["angle"] for c in g["concepts"]}), 10)
        self.assertEqual(len({c["structure"] for c in g["concepts"]}), 10)
        self.assertEqual(g["near_duplicates"], [])
        for c in g["concepts"]:
            for k in ("hook", "main_message", "proof_required", "cta", "funnel_stage", "hypothesis", "measurement", "likely_failure_points"):
                self.assertIn(k, c)

    def test_no_invented_proof(self):
        g = {c["angle"]: c for c in ads.generate_concepts(BRIEF)["concepts"]}
        self.assertNotEqual(g["customer_proof"]["readiness"], "ready")
        self.assertIn("VERIFIED_QUOTE", g["customer_proof"]["hook"].upper())
        g2 = {c["angle"]: c for c in ads.generate_concepts({**BRIEF, "proof": [{"text": "Cut my scheduling to 20 minutes", "verified": True}]})["concepts"]}
        self.assertEqual(g2["customer_proof"]["readiness"], "ready")

    def test_campaign_plan_budget_warning(self):
        p = ads.campaign_plan(BRIEF, {"daily": 20, "days": 7, "assumed_cpc": 2, "assumed_cvr": 0.03, "aov": 79, "gross_margin": 0.8})
        self.assertEqual(p["budget_projection"]["basis"], "assumption")
        self.assertIn("warning", p["budget_projection"])
        self.assertIn("launching any campaign", p["approval_required"])

    def test_registry_compare(self):
        s = KnowledgeStore()
        reg = ads.VariantRegistry(s)
        concepts = ads.generate_concepts(BRIEF)["concepts"]
        c1 = reg.register_concept(concepts[0], "P")
        self.assertEqual(reg.register_concept(concepts[0], "P"), c1)  # no duplicate
        v1 = reg.add_variant(c1, "Scheduling takes hours every week? See your whole week on one screen. Start free trial.", "meta")
        v2 = reg.add_variant(c1, "Only 2 spots left! Guaranteed results overnight.", "meta", version="v2")
        self.assertEqual(v2["qc_decision"], "reject")
        self.assertEqual(s.get(v2["variant_id"])["status"], "rejected_by_qc")
        v3 = reg.add_variant(c1, "Your techs see their jobs on their phones, unlike a whiteboard. Try it free.", "meta", version="v3")
        reg.record_result(v1["variant_id"], {"title": "wk1 v1", "metrics": {"impressions": 20000, "clicks": 600, "spend": 600, "conversions": 30}, "data_source": "platform_export"})
        reg.record_result(v3["variant_id"], {"title": "wk1 v3", "metrics": {"impressions": 20000, "clicks": 640, "spend": 600, "conversions": 52}, "data_source": "platform_export"})
        cmp = reg.compare([v1["variant_id"], v3["variant_id"]])
        self.assertEqual(len(cmp["rows"]), 2)
        self.assertIsNotNone(cmp["statistics"])
        self.assertIn(v3["variant_id"], cmp["statistics"]["decisions"])
        with self.assertRaises(Exception):
            reg.record_result(v1["variant_id"], {"title": "bad"})  # metrics missing


class FunnelTests(unittest.TestCase):
    def test_landing_audit_finds_issues_with_lines(self):
        r = funnel.audit_landing_html(HTML, "html", {"offer": SAMPLE["offer"], "primary_goal": "signup"})
        areas = {x["area"] for x in r["recommendations"]}
        for a in ("headline", "cta", "proof_trust", "forms", "mobile", "offer_clarity", "accessibility"):
            self.assertIn(a, areas)
        form = next(x for x in r["recommendations"] if x["area"] == "forms")
        self.assertIsInstance(form["line"], int)
        self.assertTrue(all(x["hypothesis"] for x in r["recommendations"]))
        self.assertFalse(any("%" in x["recommendation"] for x in r["recommendations"]))

    def test_good_page_has_fewer_high_issues(self):
        good = components.render_landing({"hero": {"headline": "Schedule your whole week in 30 minutes", "subheadline": "For HVAC owners",
                                                   "cta_text": "Start free trial"},
                                          "proof": {"items": [{"quote": "Real quote", "attribution": "Owner, verified", "verified": True}]},
                                          "lead_form": {"submit_text": "Start my free trial"}})["html"]
        bad_high = [x for x in funnel.audit_landing_html(HTML)["recommendations"] if x["severity"] == "high"]
        good_high = [x for x in funnel.audit_landing_html(good)["recommendations"] if x["severity"] == "high"]
        self.assertLess(len(good_high), len(bad_high))

    def test_jsx_audit(self):
        src = 'import x from "y";\nexport default function L(){return (<main><h1 className="h">Save {n} hours a week</h1>\n<a className="btn" href="/s">Start trial</a></main>)}'
        r = funnel.audit_landing_html(src, "jsx")
        self.assertEqual(r["summary"]["h1"], ["Save hours a week"])
        self.assertEqual(r["summary"]["ctas"], ["Start trial"])

    def test_diagnose_funnel(self):
        d = funnel.diagnose_funnel({"traffic_source": "meta", "stages": [
            {"name": "ad", "count": 5000, "message": "Schedule techs in 10 minutes"},
            {"name": "landing", "count": 4500, "message": "Enterprise field service management suite", "cta": "Buy now"},
            {"name": "signup", "count": 120}, {"name": "activation", "count": 20}, {"name": "purchase", "count": 10, "message": "Pay now"}]},
            objections=["too expensive"], follow_ups=["Here is our feature list"])
        areas = {r["area"] for r in d["recommendations"]}
        for a in ("drop_off", "consistency", "offer_traffic_match", "activation", "trust", "follow_up"):
            self.assertIn(a, areas)

    def test_onboarding(self):
        r = funnel.audit_onboarding({"steps": [{"name": "signup", "fields": 9, "est_seconds": 120}, {"name": "a"}, {"name": "b"},
                                               {"name": "c"}, {"name": "win", "delivers_value": True}],
                                     "paywall": "before_value", "email_verification_before_value": True,
                                     "upgrade_prompts": [{"trigger": "on_login", "copy": "Upgrade now"}]})
        areas = [x["area"] for x in r["recommendations"]]
        for a in ("activation", "time_to_value", "upgrade_flow", "signup_friction"):
            self.assertIn(a, areas)


class SalesTests(unittest.TestCase):
    def test_classify(self):
        self.assertEqual(sales.classify_objection("This is too expensive for us")[0]["objection"], "price")
        self.assertEqual(sales.classify_objection("I need to check with my partner")[0]["objection"], "authority")
        self.assertEqual(sales.classify_objection("Just send me some info")[0]["objection"], "send_info")

    def test_handle_includes_walk_away_and_disqualify(self):
        h = sales.handle_objection("too expensive", {"price": 1000, "buyer_budget": 200})
        self.assertEqual(h["plan"]["decision"], "offer_smaller_scope_or_disqualify")
        self.assertTrue(h["plan"]["stop_pursuing_if"])
        self.assertTrue(all(e.startswith("[NEEDED]") for e in h["plan"]["evidence_to_use"]))
        unknown = sales.handle_objection("hmm interesting")
        self.assertEqual(unknown["matches"], [])

    def test_qualify(self):
        self.assertEqual(sales.qualify({"problem": 2, "budget": 2, "authority": 2, "timing": 2, "fit": 2, "engagement": 2})["status"], "qualified")
        self.assertEqual(sales.qualify({"problem": 2, "fit": 0, "budget": 2, "authority": 2})["status"], "disqualify")
        self.assertEqual(sales.qualify({"problem": 2})["status"], "needs_discovery")
        self.assertEqual(sales.qualify({"problem": 2, "budget": 2, "authority": 2, "fit": 2, "flags": ["cannot_afford"]})["status"], "disqualify")
        with self.assertRaises(ValueError):
            sales.qualify({"problem": 5})

    def test_objection_log(self):
        log = sales.ObjectionLog(KnowledgeStore())
        log.record("Too expensive for us", "lost")
        log.record("We already use a competitor", "won")
        f = log.frequencies()
        self.assertEqual(f["total"], 2)
        self.assertIn("price", f["by_type"])

    def test_discovery(self):
        q = sales.discovery_questions("b2b_services")
        self.assertIn("What's your procurement process?", q["decision"])


class ComponentTests(unittest.TestCase):
    def test_escaping_and_proof_rules(self):
        r = components.render_landing({"hero": {"headline": "<script>alert(1)</script>", "cta_text": "Go"},
                                       "proof": {"items": [{"quote": "fake", "verified": False}]}})
        self.assertNotIn("<script>alert", r["html"])
        self.assertNotIn("fake", r["html"])
        self.assertIn('name="viewport"', r["html"])
        self.assertTrue(any("unverified" in w for w in r["warnings"]))

    def test_templates(self):
        t = components.render_template("email_abandoned_cart", {"item": "Pro plan"})
        self.assertIn("Pro plan", t["text"])
        self.assertIn("top_objection", t["missing"])
        with self.assertRaises(KeyError):
            components.render_template("email_abandoned_cart", {}, strict=True)

    def test_events(self):
        self.assertEqual(components.validate_event({"event": "cta_click", "properties": {"page": "home", "cta": "hero"}}), [])
        self.assertTrue(components.validate_event({"event": "nope"}))
        self.assertTrue(components.validate_event({"event": "purchase", "properties": {"order_id": 1, "value": "x", "currency": "USD"}}))
        self.assertEqual(components.tracking_plan(["signup", "purchase"])[1]["event"], "purchase")

    def test_jsx_template_exists(self):
        jsx = (ROOT / "marketing_toolkit" / "templates" / "LandingSections.jsx").read_text()
        for comp in ("Hero", "Proof", "Pricing", "LeadForm", "UpgradePrompt", "OnboardingChecklist"):
            self.assertIn(f"export function {comp}", jsx)
        self.assertIn("i.verified === true", jsx)


if __name__ == "__main__":
    unittest.main()
