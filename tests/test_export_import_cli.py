import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

from marketing_toolkit import export, psychology
from marketing_toolkit.store import KnowledgeStore

ROOT = Path(__file__).resolve().parent.parent
SAMPLE = json.loads((ROOT / "examples" / "marketing" / "sample_inputs.json").read_text())


def seeded_store():
    s = KnowledgeStore()
    for r in psychology.to_records(psychology.build_profile(SAMPLE["product"], "owners", SAMPLE["documents"]), "ExampleDispatch"):
        s.add(r, on_conflict="version")
    s.add({"kind": "ad_concept", "title": "Problem-led concept", "product": "ExampleDispatch", "data": {"angle": "problem_led"}})
    return s


class ExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.store = seeded_store()
        cls.results = {t: export.build_package(t, cls.store, cls.tmp.name) for t in export.TASKS}

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_all_tasks_build(self):
        self.assertEqual(set(self.results), {"app_marketing", "landing_page_optimization", "paid_ads", "sales_copy",
                                             "sales_process", "customer_research", "conversion_analysis", "marketing_full_toolkit"})
        for t, r in self.results.items():
            root = Path(r["dir"])
            for f in ("MASTER_INSTRUCTIONS.md", "USAGE.md", "METHODOLOGY.md", "CAPABILITIES.json", "CONFIG.md", "RETURN_RESULTS.md",
                      "results_template.json", "MANIFEST.json", "knowledge/knowledge_export.json", "schemas/record.json"):
                self.assertTrue((root / f).exists(), f"{t}: {f}")
            self.assertTrue(r["manifest"]["within_limit"], t)

    def test_code_included_with_dependencies(self):
        for t, r in self.results.items():
            code = Path(r["dir"]) / "code" / "marketing_toolkit"
            for m in export.TASKS[t]["modules"]:
                self.assertTrue((code / f"{m}.py").exists(), f"{t} missing {m}")
            for m in r["manifest"]["modules"]:
                self.assertTrue((code / f"{m}.py").exists())
        self.assertTrue((Path(self.results["paid_ads"]["dir"]) / "code/marketing_toolkit/experiments.py").exists())  # dep of ads
        self.assertTrue((Path(self.results["app_marketing"]["dir"]) / "code/marketing_toolkit/templates/LandingSections.jsx").exists())

    def test_task_specific_selection(self):
        cr = Path(self.results["customer_research"]["dir"]) / "code" / "marketing_toolkit"
        self.assertFalse((cr / "ads.py").exists())
        self.assertFalse((cr / "sales.py").exists())
        k = json.loads((Path(self.results["conversion_analysis"]["dir"]) / "knowledge/knowledge_export.json").read_text())
        self.assertTrue(all(r["kind"] in export.TASKS["conversion_analysis"]["kinds"] for r in k["records"]))
        ads_k = json.loads((Path(self.results["paid_ads"]["dir"]) / "knowledge/knowledge_export.json").read_text())
        self.assertIn("ad_concept", {r["kind"] for r in ads_k["records"]})

    def test_exported_code_runs_in_isolation(self):
        for t in ("conversion_analysis", "paid_ads", "marketing_full_toolkit"):
            root = Path(self.results[t]["dir"])
            code = ("import sys, json; sys.path.insert(0, 'code'); import marketing_toolkit as mt; "
                    "from marketing_toolkit import metrics; print(json.dumps(metrics.roas(300, 100)['value']))")
            out = subprocess.run([sys.executable, "-I", "-c", code], cwd=root, capture_output=True, text=True, timeout=60)
            self.assertEqual(out.returncode, 0, out.stderr)
            self.assertEqual(out.stdout.strip(), "3.0")
        root = Path(self.results["customer_research"]["dir"])
        code = ("import sys; sys.path.insert(0, 'code'); import json; from marketing_toolkit import voc; "
                "d = json.load(open('examples/marketing/sample_inputs.json')); print(voc.analyze(d['documents'])['documents_used'])")
        out = subprocess.run([sys.executable, "-I", "-c", code], cwd=root, capture_output=True, text=True, timeout=60)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(out.stdout.strip(), "8")
        # every module shipped in each package imports cleanly on its own
        for t, r in self.results.items():
            mods = [m for m in r["manifest"]["modules"] if m != "__main__"]
            code = "import sys; sys.path.insert(0, 'code'); import importlib; " + "; ".join(
                f"importlib.import_module('marketing_toolkit.{m}')" for m in mods if m != "__init__")
            out = subprocess.run([sys.executable, "-I", "-c", code], cwd=r["dir"], capture_output=True, text=True, timeout=60)
            self.assertEqual(out.returncode, 0, f"{t}: {out.stderr}")

    def test_manifest_hashes_and_zip(self):
        r = self.results["sales_copy"]
        root = Path(r["dir"])
        for f in r["manifest"]["files"][:20]:
            self.assertEqual(hashlib.sha1((root / f["path"]).read_bytes()).hexdigest(), f["sha1"])
        with zipfile.ZipFile(r["zip"]) as z:
            names = z.namelist()
        self.assertIn("sales_copy/MASTER_INSTRUCTIONS.md", names)
        self.assertIn("sales_copy/code/marketing_toolkit/copywriting.py", names)

    def test_master_instructions_require_tool_check(self):
        txt = (Path(self.results["paid_ads"]["dir"]) / "MASTER_INSTRUCTIONS.md").read_text()
        self.assertIn("Check your tools first", txt)
        self.assertIn("is **not** a tool", txt)
        caps = json.loads((Path(self.results["marketing_full_toolkit"]["dir"]) / "CAPABILITIES.json").read_text())
        types = {c["type"] for c in caps["capabilities"]}
        self.assertTrue({"python_code", "requires_runtime", "reference_code", "not_included"} <= types)

    def test_examples_are_real_outputs(self):
        ex = json.loads((Path(self.results["paid_ads"]["dir"]) / "examples/concepts.json").read_text())
        self.assertEqual(len(ex["output"]["concepts"]), 10)
        self.assertIn("ILLUSTRATIVE", ex["_note"])

    def test_size_limit_trims_knowledge(self):
        with tempfile.TemporaryDirectory() as d:
            r = export.build_package("customer_research", self.store, d, config={"export_max_bytes": 1000})
            self.assertEqual(r["manifest"]["knowledge_records"], 0)
            self.assertGreater(r["manifest"]["knowledge_trimmed"], 0)
            self.assertFalse(r["manifest"]["within_limit"])  # code is never dropped; reported honestly

    def test_unknown_task(self):
        with self.assertRaises(ValueError):
            export.build_package("nope")


class ImportTests(unittest.TestCase):
    def bundle(self, *records):
        return {"format": "marketing_toolkit.results.v1", "generated_by": "test", "records": list(records)}

    def test_import_flow_never_overwrites(self):
        s = KnowledgeStore()
        r1 = {"kind": "campaign_result", "title": "Week 1 meta", "natural_key": "res-w1", "basis": "measured",
              "data": {"metrics": {"spend": 100, "clicks": 50}}}
        rep = export.import_results(s, self.bundle(r1))
        self.assertEqual(rep["summary"]["created"], 1)
        rid = rep["created"][0]["id"]
        self.assertEqual(export.import_results(s, self.bundle(r1))["summary"]["duplicate"], 1)
        changed = dict(r1, data={"metrics": {"spend": 999, "clicks": 50}})
        rep = export.import_results(s, self.bundle(changed))
        self.assertEqual(rep["summary"]["conflicts"], 1)
        self.assertEqual(s.get(rid)["data"]["metrics"]["spend"], 100)  # untouched
        dry = export.import_results(s, self.bundle(changed), on_conflict="version", dry_run=True)
        self.assertEqual(dry["summary"]["versioned"], 1)
        self.assertEqual(s.get(rid)["data"]["metrics"]["spend"], 100)
        rep = export.import_results(s, self.bundle(changed), on_conflict="version")
        self.assertEqual(rep["summary"]["versioned"], 1)
        self.assertEqual(s.get(rid)["data"]["metrics"]["spend"], 999)
        self.assertEqual(s.history(rid)[0]["snapshot"]["data"]["metrics"]["spend"], 100)

    def test_invalid_records_reported(self):
        s = KnowledgeStore()
        rep = export.import_results(s, self.bundle({"kind": "bogus", "title": "x", "data": {}},
                                                   {"kind": "approach", "title": "Valid learning", "data": {}}))
        self.assertEqual(rep["summary"]["invalid"], 1)
        self.assertEqual(rep["summary"]["created"], 1)
        bad = export.import_results(s, {"format": "other", "records": []})
        self.assertTrue(bad["invalid"])


class CliTests(unittest.TestCase):
    def run_cli(self, *args, db):
        env = dict(os.environ, PYTHONPATH=str(ROOT))
        out = subprocess.run([sys.executable, "-m", "marketing_toolkit", "--db", db, *args], cwd=ROOT, capture_output=True,
                             text=True, env=env, timeout=120)
        self.assertEqual(out.returncode, 0, out.stderr)
        return json.loads(out.stdout)

    def test_cli_persistence_and_commands(self):
        with tempfile.TemporaryDirectory() as d:
            db = os.path.join(d, "m.db")
            docs = os.path.join(d, "docs.json")
            Path(docs).write_text(json.dumps(SAMPLE["documents"] * 2 + [
                {"id": f"s{i}", "text": f"Scheduling takes hours every week (survey {i}).", "source_type": "survey"} for i in range(5)]))
            r = self.run_cli("voc", docs, "--save", "--product", "ExampleDispatch", db=db)
            self.assertTrue(r["saved"])
            stats = self.run_cli("stats", db=db)  # new process: knowledge persisted
            self.assertGreater(stats["total"], 0)
            self.assertEqual(self.run_cli("sample-size", "0.05", "0.2", db=db)["visitors_per_arm"], 8158)
            offer = os.path.join(d, "offer.json")
            Path(offer).write_text(json.dumps(SAMPLE["offer"]))
            self.assertIn("criteria", self.run_cli("offer-score", offer, db=db))
            page = self.run_cli("audit-page", str(ROOT / "examples/marketing/sample_landing.html"), db=db)
            self.assertTrue(page["recommendations"])
            out = os.path.join(d, "pkgs")
            e = self.run_cli("export", "customer_research", "--out", out, db=db)
            self.assertGreater(e["knowledge_records"], 0)
            self.assertTrue(Path(e["zip"]).exists())
            bundle = os.path.join(d, "b.json")
            Path(bundle).write_text(json.dumps({"format": "marketing_toolkit.results.v1", "records": [
                {"kind": "approach", "title": "Loss framing lost to gain framing", "basis": "measured", "data": {}}]}))
            self.assertEqual(self.run_cli("import-results", bundle, db=db)["summary"]["created"], 1)


if __name__ == "__main__":
    unittest.main()
