import math
import unittest

from marketing_toolkit import experiments as ex
from marketing_toolkit import metrics as m
from marketing_toolkit.store import KnowledgeStore


class MetricsTests(unittest.TestCase):
    def test_basic_ratios(self):
        self.assertAlmostEqual(m.ctr(50, 1000)["value"], 0.05)
        self.assertAlmostEqual(m.cpc(100, 50)["value"], 2.0)
        self.assertAlmostEqual(m.cpm(25, 10000)["value"], 2.5)
        self.assertAlmostEqual(m.cpl(300, 20)["value"], 15.0)
        self.assertAlmostEqual(m.cpa(300, 6)["value"], 50.0)
        self.assertAlmostEqual(m.cac(5000, 25)["value"], 200.0)
        self.assertAlmostEqual(m.roas(1500, 500)["value"], 3.0)
        self.assertAlmostEqual(m.aov(1000, 8)["value"], 125.0)
        self.assertAlmostEqual(m.revenue_per_visitor(1000, 400)["value"], 2.5)
        self.assertAlmostEqual(m.lead_to_customer(5, 50)["value"], 0.1)
        self.assertAlmostEqual(m.conversion_rate(30, 1000)["value"], 0.03)

    def test_invalid_inputs_return_errors_not_exceptions(self):
        self.assertFalse(m.ctr(None, 100)["ok"])
        self.assertIn("missing", m.ctr(None, 100)["error"])
        self.assertIn("zero", m.cpc(10, 0)["error"])
        self.assertIn("negative", m.cpl(-5, 10)["error"])
        self.assertIn("not a number", m.cpa("10", 2)["error"])
        self.assertIn("inconsistent", m.ctr(200, 100)["error"])
        self.assertFalse(m.cpc(float("nan"), 3)["ok"])
        self.assertFalse(m.roas(True, 10)["ok"])

    def test_roas_is_not_profit(self):
        r = m.roas(1100, 1000)
        self.assertIn("not profit", r["note"])
        s = m.campaign_summary({"spend": 1000, "revenue": 1100, "clicks": 100, "impressions": 5000, "conversions": 10}, gross_margin_rate=0.4)
        self.assertFalse(s["profitable_on_first_purchase"])  # ROAS 1.1 < breakeven 2.5
        self.assertAlmostEqual(s["breakeven_roas"]["value"], 2.5)
        self.assertAlmostEqual(s["poas"]["value"], 0.44)

    def test_margins(self):
        self.assertAlmostEqual(m.gross_margin(100, 40)["value"], 0.6)
        self.assertAlmostEqual(m.gross_margin(100, 140)["value"], -0.4)
        self.assertFalse(m.gross_margin(0, 10)["ok"])
        cm = m.contribution_margin(100, 30, 50)
        self.assertEqual((cm["value"], cm["rate"]), (20, 0.2))
        self.assertFalse(m.breakeven_roas(0)["ok"])
        self.assertFalse(m.breakeven_roas(1.5)["ok"])

    def test_ltv_payback_churn(self):
        self.assertAlmostEqual(m.ltv(50, 0.8, 0.05)["value"], 800)
        capped = m.ltv(50, 0.8, 0.05, max_periods=12)["value"]
        self.assertAlmostEqual(capped, 40 * (1 - 0.95 ** 12) / 0.05, places=4)
        self.assertFalse(m.ltv(50, 0.8, 0)["ok"])
        self.assertAlmostEqual(m.payback_months(300, 50)["value"], 6)
        self.assertIn("never", m.payback_months(300, 0)["error"])
        self.assertIn("unprofitable", m.payback_months(600, 20, 0.1)["note"])
        self.assertAlmostEqual(m.churn_rate(5, 100)["value"], 0.05)
        self.assertAlmostEqual(m.retention_rate(110, 20, 100)["value"], 0.9)
        self.assertFalse(m.retention_rate(150, 0, 100)["ok"])
        self.assertAlmostEqual(m.ltv_to_cac(900, 300)["value"], 3)

    def test_funnel(self):
        f = m.funnel([{"name": "visit", "count": 1000}, {"name": "signup", "count": 100}, {"name": "pay", "count": 20}])
        self.assertTrue(f["ok"])
        self.assertEqual(f["largest_drop"], "signup")
        self.assertAlmostEqual(f["stages"][2]["step_conversion"], 0.2)
        self.assertAlmostEqual(f["overall_conversion"], 0.02)
        bad = m.funnel([{"name": "a", "count": 10}, {"name": "b", "count": 20}])
        self.assertFalse(bad["ok"])
        self.assertFalse(m.funnel([{"name": "a", "count": -1}, {"name": "b", "count": 1}])["ok"])

    def test_unit_economics_and_scenarios(self):
        ue = m.unit_economics(79, 12, 1, 250, monthly=True, churn=0.05)
        self.assertAlmostEqual(ue["ltv"]["value"], 67 / 0.05)
        sc = m.scenarios({"price": 79, "cogs_per_order": 12, "orders_per_customer": 1, "cac_value": 250, "monthly": True, "churn": 0.05},
                         {"price_up": {"price": "+10%"}, "churn_up": {"churn": 0.1}})
        self.assertGreater(sc["price_up"]["delta_profit_per_customer"], 0)
        self.assertLess(sc["churn_up"]["delta_profit_per_customer"], 0)
        one_off = m.unit_economics(100, 40, 3, 90)
        self.assertEqual(one_off["profit_per_customer"], 90)


class StatsTests(unittest.TestCase):
    def test_norm(self):
        self.assertAlmostEqual(ex.norm_ppf(0.975), 1.959964, places=5)
        self.assertAlmostEqual(ex.norm_ppf(0.5), 0.0, places=7)
        for p in (0.001, 0.02, 0.3, 0.9, 0.999):
            self.assertAlmostEqual(ex.norm_cdf(ex.norm_ppf(p)), p, places=8)

    def test_sample_size_known_value(self):
        # 5% baseline, 20% relative MDE, alpha .05, power .8 -> ~8.2k per arm (standard calculators agree)
        self.assertTrue(8100 <= ex.sample_size_per_arm(0.05, 0.2) <= 8200)
        self.assertGreater(ex.sample_size_per_arm(0.05, 0.1), ex.sample_size_per_arm(0.05, 0.2))
        with self.assertRaises(ValueError):
            ex.sample_size_per_arm(0, 0.1)

    def test_two_proportion(self):
        t = ex.two_proportion_test(200, 4000, 260, 4000)
        # pooled z = 0.015 / sqrt(.0575*.9425*(2/4000)) = 0.015 / 0.0052055 = 2.8816
        self.assertAlmostEqual(t["z"], 2.8816, places=3)
        self.assertAlmostEqual(t["p_value"], 2 * (1 - ex.norm_cdf(t["z"])), places=12)
        self.assertLess(t["diff_ci"][0], 0.015 < t["diff_ci"][1])
        with self.assertRaises(ValueError):
            ex.two_proportion_test(10, 5, 1, 10)

    def test_wilson(self):
        lo, hi = ex.wilson_interval(10, 100)
        self.assertAlmostEqual(lo, 0.0552, places=3)
        self.assertAlmostEqual(hi, 0.1744, places=3)
        self.assertAlmostEqual(ex.wilson_interval(0, 10)[0], 0.0, places=12)

    def test_holm(self):
        r = ex.holm_correction({"a": 0.01, "b": 0.03, "c": 0.04})
        self.assertTrue(r["a"]["significant"])   # .01 <= .05/3
        self.assertFalse(r["b"]["significant"])  # .03 >  .05/2
        self.assertFalse(r["c"]["significant"])  # step-down stops after first failure
        self.assertTrue(all(v["significant"] for v in ex.holm_correction({"a": 0.01, "b": 0.02, "c": 0.04}).values()))

    def test_no_winner_on_small_samples(self):
        a = ex.analyze({"control": {"n": 100, "conversions": 2}, "B": {"n": 100, "conversions": 9}}, "control")
        self.assertEqual(a["decisions"]["B"], "inconclusive")
        self.assertTrue(a["data_warnings"])

    def test_winner_and_practical_significance(self):
        arms = {"control": {"n": 20000, "conversions": 1000}, "B": {"n": 20000, "conversions": 1110}}
        self.assertEqual(ex.analyze(arms, "control", mde_relative=0.05)["decisions"]["B"], "variant_wins")
        self.assertEqual(ex.analyze(arms, "control", mde_relative=0.2)["decisions"]["B"], "significant_but_not_practical")

    def test_guardrail(self):
        arms = {"control": {"n": 20000, "conversions": 1000}, "B": {"n": 20000, "conversions": 1200}}
        a = ex.analyze(arms, "control", guardrails={"refund_rate": {"control": 0.02, "B": 0.05, "max_increase": 0.01}})
        self.assertEqual(a["decisions"]["B"], "reject_variant_guardrail")

    def test_multiple_variants_use_holm(self):
        arms = {"control": {"n": 5000, "conversions": 250}, "B": {"n": 5000, "conversions": 290},
                "C": {"n": 5000, "conversions": 252}}
        a = ex.analyze(arms, "control")
        self.assertIn("holm_threshold", a["multiple_comparison"]["B"])


class ManagerTests(unittest.TestCase):
    def test_lifecycle_and_failed_log(self):
        s = KnowledgeStore()
        em = ex.ExperimentManager(s)
        eid = em.create({"hypothesis": "Outcome headline beats feature headline on signups", "funnel_stage": "landing",
                         "category": "headline", "control": "feature", "variant": "outcome", "primary_metric": "signup_rate",
                         "baseline_rate": 0.04, "minimum_detectable_effect": 0.1})
        self.assertEqual(em.get(eid)["data"]["experiment_id"], eid)
        self.assertGreater(em.get(eid)["data"]["planned_n_per_arm"], 1000)
        em.start(eid, "2026-10-01")
        em.record_data(eid, {"control": {"n": 400, "conversions": 16}, "B": {"n": 410, "conversions": 15}}, source="analytics export")
        self.assertEqual(em.analyze(eid)["decisions"]["B"], "keep_running")
        em.conclude(eid, "inconclusive", "Traffic too low for headline tests; test bigger changes")
        self.assertEqual(em.get(eid)["data"]["status"], "inconclusive")
        self.assertEqual(len(em.failed_tests()), 1)
        self.assertGreaterEqual(len(s.history(eid)), 3)

    def test_create_if_exists(self):
        em = ex.ExperimentManager(KnowledgeStore())
        spec = {"experiment_id": "e1", "hypothesis": "A long enough hypothesis here", "funnel_stage": "signup",
                "control": "a", "variant": "b", "primary_metric": "x"}
        eid = em.create(spec)
        em.record_data(eid, {"control": {"n": 10, "conversions": 1}})
        with self.assertRaises(Exception):
            em.create(spec)
        self.assertEqual(em.create(spec, if_exists="return"), eid)

    def test_validation(self):
        em = ex.ExperimentManager(KnowledgeStore())
        with self.assertRaises(Exception):
            em.create({"hypothesis": "short", "funnel_stage": "nowhere", "control": "a", "variant": "b", "primary_metric": "x"})
        eid = em.create({"hypothesis": "A long enough hypothesis here", "funnel_stage": "signup", "control": "a",
                         "variant": "b", "primary_metric": "x"})
        with self.assertRaises(ValueError):
            em.record_data(eid, {"control": {"n": 10}})
        with self.assertRaises(ValueError):
            em.analyze(eid)


if __name__ == "__main__":
    unittest.main()
