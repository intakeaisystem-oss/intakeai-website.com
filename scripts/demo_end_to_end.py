#!/usr/bin/env python3
"""End-to-end acceptance demo for marketing_toolkit (stdlib only).

Runs every system on the ILLUSTRATIVE sample inputs against a separate demo
database (data/demo.db, never your real store), then prints a checklist of
acceptance criteria with PASS/FAIL. Run twice to see persistence between runs.

    python3 scripts/demo_end_to_end.py [--reset]
"""

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from marketing_toolkit import (ads, copywriting, experiments, export, funnel, metrics,  # noqa: E402
                               offer, psychology, qc, sales, voc)
from marketing_toolkit.store import KnowledgeStore  # noqa: E402

checks = []


def check(name, ok, detail=""):
    checks.append((name, bool(ok), detail))


def main():
    db = ROOT / "data" / "demo.db"
    if "--reset" in sys.argv and db.exists():
        db.unlink()
    existed = db.exists()
    s = KnowledgeStore(str(db))
    before = s.stats()["total"]
    sample = json.loads((ROOT / "examples/marketing/sample_inputs.json").read_text())
    html = (ROOT / "examples/marketing/sample_landing.html").read_text()
    P = "ExampleDispatch (demo)"

    # 1 customer research -> structured findings
    v = voc.analyze(sample["documents"], competitors=sample["product"]["alternatives"])
    prof = psychology.build_profile(sample["product"], "small HVAC/plumbing owners", sample["documents"], v)
    saved = [s.add(r, on_conflict="version") for r in psychology.to_records(prof, P)]
    check("Customer research -> structured findings", prof["evidence_summary"]["observed_insights"] > 0 and saved,
          f"{prof['evidence_summary']['observed_insights']} observed insights, {len(saved)} records")

    # 2 offer + copy evaluation with configurable criteria
    o = offer.score_offer(sample["offer"])
    o2 = offer.score_offer(sample["offer"], {"offer_weights": {"proof": 10}})
    c = copywriting.evaluate_copy({"text": sample["copy"], "offer": sample["offer"], "kind": "landing",
                                   "audience_terms": ["techs", "scheduling"]})
    s.add(offer.to_record(sample["offer"], o, P), on_conflict="version")
    s.add(copywriting.to_record(sample["copy"], c, "landing_page", P), on_conflict="version")
    check("Offers and copy evaluated against configurable criteria", o["overall"] != o2["overall"] and len(c["criteria"]) == 12,
          f"offer {o['overall']} (proof-weighted {o2['overall']}), copy {c['overall']} qc={c['qc']['decision']}")

    # 3 ad concepts + variants stored and compared
    reg = ads.VariantRegistry(s)
    g = ads.generate_concepts({"offer": sample["offer"], "pains": ["Scheduling takes hours every week."],
                               "outcomes": [sample["offer"]["desired_outcome"]], "objections": ["too expensive for a small shop"],
                               "audience": "small HVAC owners", "job": "schedule a week of jobs", "cta": "Start free trial"})
    cid = reg.register_concept(g["concepts"][0], P)
    va = reg.add_variant(cid, "\"Scheduling takes hours every week.\" Sound familiar? See every tech's week on one screen. Start free trial.", "meta")
    vb = reg.add_variant(cid, "Your techs see their jobs on their phones, unlike a whiteboard. Start free trial.", "meta", version="v2")
    if not reg.results_for(va["variant_id"]):
        reg.record_result(va["variant_id"], {"title": "demo week 1 A", "data_source": "manual",
                                             "metrics": {"impressions": 24000, "clicks": 700, "spend": 700, "conversions": 28},
                                             "notes": "ILLUSTRATIVE demo numbers"})
        reg.record_result(vb["variant_id"], {"title": "demo week 1 B", "data_source": "manual",
                                             "metrics": {"impressions": 24000, "clicks": 720, "spend": 700, "conversions": 47},
                                             "notes": "ILLUSTRATIVE demo numbers"})
    cmp = reg.compare([va["variant_id"], vb["variant_id"]])
    check("Ad concepts and variants stored and compared", len(g["concepts"]) == 10 and cmp["statistics"],
          f"decision: {cmp['statistics']['decisions'] if cmp['statistics'] else None}")

    # 4 funnel + landing audits are actionable
    la = funnel.audit_landing_html(html, "html", {"offer": sample["offer"], "ad_text": sample["copy"], "primary_goal": "signup"})
    fd = funnel.diagnose_funnel(sample["funnel"])
    s.add(funnel.to_record(la, "Demo landing audit", P), on_conflict="version")
    check("Funnel and landing audits produce actionable findings",
          la["recommendations"] and all(r["recommendation"] and r["hypothesis"] for r in la["recommendations"]),
          f"{len(la['recommendations'])} page recs, {len(fd['recommendations'])} funnel recs")

    # 5 metrics correct
    mm = metrics.campaign_summary(sample["campaign_metrics"], 0.85)
    check("Marketing metrics calculate correctly",
          abs(mm["ctr"]["value"] - 0.02) < 1e-9 and abs(mm["cpc"]["value"] - 1.25) < 1e-9 and not metrics.ctr(5, 0)["ok"],
          f"CTR {mm['ctr']['value']}, CPC {mm['cpc']['value']}, ROAS {mm['roas']['value']} vs breakeven {mm['breakeven_roas']['value']:.3f}")

    # 6 experiments created, updated, analyzed
    em = experiments.ExperimentManager(s)
    eid = em.create({"experiment_id": "demo-headline-01", "hypothesis": "Outcome headline beats feature headline on trial starts",
                     "funnel_stage": "landing", "category": "headline", "control": "feature headline", "variant": "outcome headline",
                     "primary_metric": "trial_start_rate", "baseline_rate": 0.04, "minimum_detectable_effect": 0.15}, P,
                    if_exists="return")
    em.record_data(eid, sample["experiment_arms"], source="ILLUSTRATIVE demo data")
    an = em.analyze(eid)
    check("Experiments created, updated and analysed", eid and an["decisions"], f"{eid}: {an['decisions']} warnings={len(an['data_warnings'])}")

    # sales
    h = sales.handle_objection("Looks good but it's too expensive for a small shop like mine", {"price": 79})
    sales.ObjectionLog(s).record("Looks good but it's too expensive for a small shop like mine", "open", P, source_ref="example-call-1")

    # 7 persistence
    after = s.stats()
    check("Marketing knowledge persists between runs", after["total"] >= before and (not existed or before > 0),
          f"records before this run: {before}, after: {after['total']} (run again to confirm)")

    # 8/9 export packages contain code + instructions
    out = Path(tempfile.mkdtemp())
    pk = export.build_package("paid_ads", s, str(out), product=P)
    code_ok = all((Path(pk["dir"]) / "code/marketing_toolkit" / f"{m}.py").exists() for m in export.TASKS["paid_ads"]["modules"])
    check("Task-specific packages export for normal Claude", Path(pk["zip"]).exists(), pk["zip"])
    check("Package includes actual code and instructions", code_ok and (Path(pk["dir"]) / "MASTER_INSTRUCTIONS.md").exists(),
          f"{len(pk['manifest']['modules'])} modules, {pk['manifest']['knowledge_records']} knowledge records")

    # 10 import does not silently overwrite
    rid_exp = em.get(eid)
    bundle = {"format": "marketing_toolkit.results.v1", "records": [
        {"kind": "experiment", "title": "conflicting copy of the experiment", "natural_key": "demo-headline-01",
         "data": {"hypothesis": "tampered"}}]}
    rep = export.import_results(s, bundle)
    check("Importing results does not silently overwrite", rep["summary"]["conflicts"] == 1 and
          s.get(rid_exp["id"])["data"]["hypothesis"] == rid_exp["data"]["hypothesis"], f"report: {rep['summary']}")

    # qc sanity
    bad = qc.evaluate("Only 3 spots left! Guaranteed results overnight.", {"kind": "ad"})
    check("QC rejects misleading output", bad["decision"] == "reject", f"{[f['code'] for f in bad['findings']]}")
    s.close()

    width = max(len(n) for n, _, _ in checks)
    for n, ok, d in checks:
        print(f"[{'PASS' if ok else 'FAIL'}] {n.ljust(width)}  {d}")
    print(f"\n{sum(ok for _, ok, _ in checks)}/{len(checks)} acceptance checks passed (demo DB: {db})")
    return 0 if all(ok for _, ok, _ in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
