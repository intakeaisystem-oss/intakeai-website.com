"""Command line interface:  python -m marketing_toolkit <command> ...

Input files are JSON unless noted. Output is JSON on stdout. Commands that
persist data use the store at config db_path (override with --db).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import ads, copywriting, experiments, export, funnel, metrics, offer, psychology, qc, sales, voc
from .config import load_config
from .store import KnowledgeStore


def _load(path: str):
    return json.loads(Path(path).read_text())


def _out(obj) -> None:
    json.dump(obj, sys.stdout, indent=2, default=str, ensure_ascii=False)
    sys.stdout.write("\n")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="marketing_toolkit", description=__doc__)
    ap.add_argument("--db", help="SQLite path (default from config)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("voc", help="analyze customer documents: JSON list of {id,text,source_type,source_ref}")
    s.add_argument("documents"); s.add_argument("--competitors", nargs="*", default=[])
    s.add_argument("--save", action="store_true"); s.add_argument("--product"); s.add_argument("--audience")

    s = sub.add_parser("profile", help="build customer profile: JSON {product:{}, documents:[], audience:''}")
    s.add_argument("input"); s.add_argument("--save", action="store_true")

    s = sub.add_parser("offer-score", help="score an offer JSON"); s.add_argument("offer"); s.add_argument("--save", action="store_true")
    s = sub.add_parser("offer-structures", help="generate offer structures"); s.add_argument("offer")

    s = sub.add_parser("copy-eval", help="evaluate copy: JSON {text, offer?, channel?, audience_terms?, known_objections?, kind?}")
    s.add_argument("input"); s.add_argument("--save", action="store_true"); s.add_argument("--asset-type", default="copy")
    s = sub.add_parser("copy-draft", help="framework skeleton: JSON brief"); s.add_argument("framework"); s.add_argument("brief")

    s = sub.add_parser("qc", help="quality-control a text file"); s.add_argument("textfile"); s.add_argument("--context")

    s = sub.add_parser("ad-concepts", help="generate creative concepts from a JSON brief"); s.add_argument("brief")
    s.add_argument("--save", action="store_true"); s.add_argument("--product")
    s = sub.add_parser("campaign-plan", help="campaign plan: JSON {brief:{}, budget:{}}"); s.add_argument("input")

    s = sub.add_parser("audit-page", help="audit an HTML/JSX/TSX/Vue file"); s.add_argument("file"); s.add_argument("--context")
    s.add_argument("--save", action="store_true"); s.add_argument("--product")
    s = sub.add_parser("funnel", help="diagnose a funnel JSON {stages:[{name,count,message?,cta?}], traffic_source?}"); s.add_argument("input")
    s = sub.add_parser("onboarding", help="audit onboarding spec JSON"); s.add_argument("input")

    s = sub.add_parser("metrics", help="campaign summary from metrics JSON"); s.add_argument("input"); s.add_argument("--gross-margin", type=float)
    s = sub.add_parser("unit-economics", help="unit economics + scenarios: JSON {base:{}, changes:{}}"); s.add_argument("input")

    s = sub.add_parser("exp-create", help="create experiment from JSON spec"); s.add_argument("spec"); s.add_argument("--product")
    s = sub.add_parser("exp-data", help="record arm data: JSON {control:{n,conversions}, B:{...}}"); s.add_argument("id"); s.add_argument("arms")
    s.add_argument("--source", default="manual")
    s = sub.add_parser("exp-analyze", help="analyze stored experiment"); s.add_argument("id")
    s = sub.add_parser("exp-conclude", help="conclude experiment"); s.add_argument("id"); s.add_argument("decision"); s.add_argument("learnings")
    s = sub.add_parser("sample-size", help="visitors per arm"); s.add_argument("baseline", type=float); s.add_argument("mde", type=float)

    s = sub.add_parser("objection", help="objection handling plan"); s.add_argument("text"); s.add_argument("--context")
    s = sub.add_parser("qualify", help="qualify lead JSON"); s.add_argument("lead")

    s = sub.add_parser("find", help="search the store"); s.add_argument("--kind"); s.add_argument("--product"); s.add_argument("--text")
    s.add_argument("--limit", type=int, default=50)
    sub.add_parser("stats", help="store statistics")
    s = sub.add_parser("history", help="record history"); s.add_argument("id")

    s = sub.add_parser("export", help="build a package for normal Claude")
    s.add_argument("task", choices=sorted(export.TASKS)); s.add_argument("--product"); s.add_argument("--audience")
    s.add_argument("--out"); s.add_argument("--no-zip", action="store_true")
    s = sub.add_parser("import-results", help="import a results bundle JSON safely")
    s.add_argument("bundle"); s.add_argument("--on-conflict", choices=["error", "skip", "version"], default="error")
    s.add_argument("--dry-run", action="store_true")

    a = ap.parse_args(argv)
    cfg = load_config()
    store = KnowledgeStore(a.db or cfg["db_path"])

    def save(records):
        return [dict(zip(("id", "action"), store.add(r, on_conflict="version"))) for r in records]

    c = a.cmd
    if c == "voc":
        r = voc.analyze(_load(a.documents), competitors=a.competitors)
        if a.save:
            r["saved"] = save(voc.to_records(r, a.product, a.audience))
        _out(r)
    elif c == "profile":
        d = _load(a.input)
        r = psychology.build_profile(d["product"], d.get("audience", ""), d.get("documents"), competitors=d.get("competitors"))
        if a.save:
            r["saved"] = save(psychology.to_records(r, d["product"].get("name"), d.get("audience") or None))
        _out(r)
    elif c == "offer-score":
        o = _load(a.offer); r = offer.score_offer(o)
        if a.save:
            r["saved"] = save([offer.to_record(o, r)])
        _out(r)
    elif c == "offer-structures":
        _out(offer.generate_structures(_load(a.offer)))
    elif c == "copy-eval":
        d = _load(a.input); r = copywriting.evaluate_copy(d)
        if a.save:
            r["saved"] = save([copywriting.to_record(d["text"], r, a.asset_type)])
        _out(r)
    elif c == "copy-draft":
        _out(copywriting.build_draft(a.framework, _load(a.brief)))
    elif c == "qc":
        _out(qc.evaluate(Path(a.textfile).read_text(), _load(a.context) if a.context else None))
    elif c == "ad-concepts":
        r = ads.generate_concepts(_load(a.brief))
        if a.save:
            reg = ads.VariantRegistry(store)
            r["saved"] = [reg.register_concept(x, a.product) for x in r["concepts"]]
        _out(r)
    elif c == "campaign-plan":
        d = _load(a.input); _out(ads.campaign_plan(d["brief"], d.get("budget")))
    elif c == "audit-page":
        r = funnel.audit_file(a.file, _load(a.context) if a.context else None)
        if a.save:
            r["saved"] = save([funnel.to_record(r, f"Landing audit: {a.file}", a.product)])
        _out(r)
    elif c == "funnel":
        _out(funnel.diagnose_funnel(_load(a.input)))
    elif c == "onboarding":
        _out(funnel.audit_onboarding(_load(a.input)))
    elif c == "metrics":
        _out(metrics.campaign_summary(_load(a.input), a.gross_margin))
    elif c == "unit-economics":
        d = _load(a.input); _out(metrics.scenarios(d["base"], d.get("changes", {})))
    elif c == "exp-create":
        _out({"id": experiments.ExperimentManager(store).create(_load(a.spec), a.product)})
    elif c == "exp-data":
        _out(experiments.ExperimentManager(store).record_data(a.id, _load(a.arms), source=a.source))
    elif c == "exp-analyze":
        _out(experiments.ExperimentManager(store).analyze(a.id))
    elif c == "exp-conclude":
        _out(experiments.ExperimentManager(store).conclude(a.id, a.decision, a.learnings))
    elif c == "sample-size":
        _out({"visitors_per_arm": experiments.sample_size_per_arm(a.baseline, a.mde, cfg["alpha"], cfg["power"])})
    elif c == "objection":
        _out(sales.handle_objection(a.text, _load(a.context) if a.context else None))
    elif c == "qualify":
        _out(sales.qualify(_load(a.lead)))
    elif c == "find":
        _out(store.find(kind=a.kind, product=a.product, text=a.text, limit=a.limit))
    elif c == "stats":
        _out(store.stats())
    elif c == "history":
        _out(store.history(a.id))
    elif c == "export":
        r = export.build_package(a.task, store, a.out, a.product, a.audience, make_zip=not a.no_zip)
        _out({"dir": r["dir"], "zip": r["zip"], "files": len(r["manifest"]["files"]), "bytes": r["manifest"]["total_bytes"],
              "within_limit": r["manifest"]["within_limit"], "knowledge_records": r["manifest"]["knowledge_records"]})
    elif c == "import-results":
        _out(export.import_results(store, a.bundle, a.on_conflict, a.dry_run))
    store.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
