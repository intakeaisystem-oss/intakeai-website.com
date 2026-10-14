#!/usr/bin/env python3
"""Tests for the validator: the real repo passes, and broken inputs are caught. Stdlib unittest."""

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bundle  # noqa: E402
import validate  # noqa: E402

ROOT = validate.ROOT
GOOD_TASK = ROOT / "examples" / "sample-job" / "tasks" / "TASK-03-paying-customer-evidence.md"


class RepoPasses(unittest.TestCase):
    def test_full_system_valid(self):
        r = validate.run_all(ROOT)
        self.assertEqual(r.failures, [], "\n".join(r.failures))
        self.assertGreater(r.passed, 200)

    def test_example_result_valid(self):
        self.assertEqual(validate.lint_result(GOOD_TASK), [])

    def test_bundle_builds(self):
        bundle.main()
        text = (ROOT / "dist" / "PROJECT_KNOWLEDGE.md").read_text()
        for name in validate.AGENTS:
            self.assertIn(f".claude/agents/{name}.md", text)
        self.assertIn("OUTPUT_SCHEMA", text)


class BrokenInputsCaught(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.repo = self.tmp / "repo"
        shutil.copytree(ROOT, self.repo, ignore=shutil.ignore_patterns(".git", "dist", "__pycache__"))

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def failures(self):
        return validate.run_all(self.repo).failures

    def edit(self, rel, old, new):
        p = self.repo / rel
        text = p.read_text()
        self.assertIn(old, text)
        p.write_text(text.replace(old, new, 1))

    def test_missing_agent(self):
        (self.repo / ".claude/agents/skeptic-risk.md").unlink()
        self.assertTrue(any("skeptic-risk" in f for f in self.failures()))

    def test_agent_with_spawn_tool(self):
        self.edit(".claude/agents/market-intelligence.md", "tools: WebSearch", "tools: Agent, WebSearch")
        self.assertTrue(any("must not have" in f for f in self.failures()))

    def test_agent_missing_safety_rules(self):
        p = self.repo / ".claude/agents/unit-economics.md"
        p.write_text(p.read_text().split("## Shared operating rules")[0])
        f = self.failures()
        self.assertTrue(any("unit-economics: missing shared operating rules" in x for x in f))
        self.assertTrue(any("unit-economics: missing no-fabrication rule" in x for x in f))

    def test_name_mismatch(self):
        self.edit(".claude/agents/sales-psychology.md", "name: sales-psychology", "name: sales")
        self.assertTrue(any("frontmatter name" in f for f in self.failures()))

    def test_memory_agent_with_web(self):
        self.edit(".claude/agents/knowledge-memory.md", "tools: Read", "tools: WebSearch, Read")
        self.assertTrue(any("should not have web tools" in f for f in self.failures()))

    def test_secret_detected(self):
        (self.repo / "vault" / "ResearchOS" / "leak.md").write_text("key: sk-ant-api03-" + "a" * 40)
        self.assertTrue(any("secrets" in f for f in self.failures()))

    def test_bad_config_limit(self):
        self.edit("research.config.md", "max_concurrent_agents: 4", "max_concurrent_agents: 0")
        self.assertTrue(any("max_concurrent_agents" in f for f in self.failures()))

    def test_missing_vault_file(self):
        (self.repo / "vault/ResearchOS/Rejected Opportunities.md").unlink()
        self.assertTrue(any("Rejected Opportunities" in f for f in self.failures()))

    def test_example_with_real_url(self):
        self.edit("examples/sample-job/report.md", "Bottom line", "Bottom line https://realcompany.io/pricing")
        self.assertTrue(any("non-placeholder URL" in f for f in self.failures()))

    def test_invalid_yaml_description(self):
        self.edit(".claude/agents/unit-economics.md", "description: Unit", "description: Note: Unit")
        self.assertTrue(any("invalid YAML" in f for f in self.failures()))

    def test_skill_missing_limit(self):
        self.edit(".claude/skills/research/SKILL.md", "max_retries_per_task", "retries")
        self.assertTrue(any("max_retries_per_task" in f for f in self.failures()))


class ResultLinter(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.path = self.tmp / "TASK-03-paying-customer-evidence.md"
        self.good = GOOD_TASK.read_text()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def lint(self, text):
        self.path.write_text(text)
        return validate.lint_result(self.path)

    def test_uncited_source_id(self):
        probs = self.lint(self.good.replace("| SRC-8a9b0c1d | Restaurant", "| SRC-zzzz | Restaurant"))
        self.assertTrue(any("not in Sources table" in p for p in probs))

    def test_verified_fact_without_source(self):
        probs = self.lint(self.good.replace("grease traps. [SRC-0e1a2b3c]", "grease traps."))
        self.assertTrue(any("verified fact without source" in p for p in probs))

    def test_spending_claim_without_source(self):
        probs = self.lint(self.good.replace("| customer-spending | SRC-4d5e6f70 |", "| customer-spending | none |"))
        self.assertTrue(any("without source" in p for p in probs))

    def test_unknown_evidence_category(self):
        probs = self.lint(self.good.replace("| customer-problem |", "| vibes |"))
        self.assertTrue(any("unknown evidence category" in p for p in probs))

    def test_missing_section(self):
        probs = self.lint(self.good.replace("## Contradictory evidence", "## Other"))
        self.assertTrue(any("Contradictory evidence" in p for p in probs))

    def test_bad_status_and_mode(self):
        probs = self.lint(self.good.replace("status: complete", "status: done").replace("mode: live", "mode: mock"))
        self.assertTrue(any("bad status" in p for p in probs))
        self.assertTrue(any("bad mode" in p for p in probs))

    def test_task_id_filename_mismatch(self):
        probs = self.lint(self.good.replace("task_id: TASK-03-paying-customer-evidence", "task_id: TASK-99-x"))
        self.assertTrue(any("!= task_id" in p for p in probs))


if __name__ == "__main__":
    unittest.main(verbosity=1)
