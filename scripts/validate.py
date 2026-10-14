#!/usr/bin/env python3
"""Structural validator for the 10-agent research system (stdlib only).

Usage:
  python3 scripts/validate.py                 # validate the whole system
  python3 scripts/validate.py --results DIR   # lint task result files in a job folder (DIR/tasks/*.md or DIR/*.md)

Exit code 0 = all checks passed, 1 = failures.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

AGENTS = [
    "market-intelligence", "paying-customer-evidence", "sales-psychology",
    "marketing-distribution", "unit-economics", "competitor-intelligence",
    "ai-tools-automation", "knowledge-memory", "skeptic-risk", "chief-orchestrator",
]
ALLOWED_TOOLS = {"WebSearch", "WebFetch", "Read", "Grep", "Glob", "Write", "Edit"}
SPAWN_TOOLS = {"Agent", "Task", "Bash"}  # workers must not spawn agents or run shell commands
NO_WEB = {"knowledge-memory", "chief-orchestrator"}

RESULT_FRONTMATTER = ["task_id", "job_id", "agent", "role", "research_question",
                      "status", "confidence", "mode", "timestamp", "sources"]
RESULT_SECTIONS = ["Research question", "Summary", "Findings", "Verified facts",
                   "Estimates and assumptions", "Contradictory evidence", "Limitations",
                   "Recommended next steps", "Sources"]
STATUSES = {"complete", "partial", "blocked", "failed"}
CONFIDENCES = {"low", "medium", "high"}
MODES = {"live", "offline"}
EVIDENCE = {"direct-commercial", "customer-spending", "customer-problem", "market-signal",
            "estimate", "hypothesis", "unverified"}

CONFIG_KEYS = ["vault_path", "system_folder", "knowledge_dirs", "max_concurrent_agents",
               "max_subtasks_per_job", "max_retries_per_task", "max_web_searches_per_agent",
               "max_job_minutes", "max_claims_for_skeptic", "reuse_days", "research_spend_limit_usd"]

VAULT_FILES = ["00 Research Index.md", "Dashboard.md", "Agent Registry.md", "Task Queue.md",
               "Research Backlog.md", "Decision Log.md", "Rejected Opportunities.md",
               "Session History.md", "RESUME.md"]
VAULT_DIRS = ["Jobs", "Opportunities", "Sources", "Findings", "Sessions", "Templates"]
TEMPLATES = ["Job.md", "Task.md", "Opportunity.md", "Source.md", "Finding.md", "Report.md", "Decision.md"]
DOCS = ["README.md", "SYSTEM_ARCHITECTURE.md", "AGENTS.md", "CLAUDE_HANDOFF.md", "OPERATIONS_GUIDE.md",
        "CONFIGURATION.md", "SECURITY.md", "TESTING.md", "ROADMAP.md", ".env.example", "CLAUDE.md"]

SECRET_PATTERNS = [
    re.compile(r"sk-ant-[A-Za-z0-9_\-]{16,}"),
    re.compile(r"\bsk-[A-Za-z0-9]{32,}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bxox[baprs]-[A-Za-z0-9\-]{20,}\b"),
    re.compile(r"(?im)^[ \t]*[A-Z_]*(API_KEY|SECRET|TOKEN|PASSWORD)[ \t]*=[ \t]*\S{8,}"),
]


# ---------------------------------------------------------------- helpers
def frontmatter(text: str) -> tuple[dict, str] | tuple[None, str]:
    m = re.match(r"\A---\r?\n(.*?)\r?\n---\r?\n?", text, re.S)
    if not m:
        return None, text
    meta: dict = {}
    for line in m.group(1).splitlines():
        kv = re.match(r"^([A-Za-z0-9_\-]+)\s*:\s*(.*?)\s*(#.*)?$", line)
        if not kv:
            continue
        val = kv.group(2).strip()
        if val.startswith("[") and val.endswith("]"):
            meta[kv.group(1)] = [v.strip().strip("\"'") for v in val[1:-1].split(",") if v.strip()]
        else:
            meta[kv.group(1)] = val.strip("\"'")
    return meta, text[m.end():]


def yaml_unsafe_lines(text: str) -> list[str]:
    """Unquoted frontmatter values containing ': ' break real YAML parsers (Claude Code uses one)."""
    m = re.match(r"\A---\r?\n(.*?)\r?\n---", text, re.S)
    bad = []
    for line in (m.group(1).splitlines() if m else []):
        kv = re.match(r"^[A-Za-z0-9_\-]+\s*:\s*(.*)$", line)
        if kv and kv.group(1) and kv.group(1)[0] not in "\"'[{" and re.search(r":\s", kv.group(1)):
            bad.append(line[:50])
    return bad


class Report:
    def __init__(self):
        self.failures: list[str] = []
        self.passed = 0

    def check(self, ok: bool, msg: str):
        if ok:
            self.passed += 1
        else:
            self.failures.append(msg)
        return ok


# ---------------------------------------------------------------- checks
def check_agents(r: Report, root: Path):
    adir = root / ".claude" / "agents"
    found = sorted(p.stem for p in adir.glob("*.md"))
    r.check(sorted(AGENTS) == found, f"agents: expected exactly {len(AGENTS)} agents {AGENTS}, found {found}")
    for name in AGENTS:
        p = adir / f"{name}.md"
        if not r.check(p.exists(), f"agents: missing {p}"):
            continue
        meta, body = frontmatter(p.read_text())
        if not r.check(meta is not None, f"{name}: no frontmatter"):
            continue
        r.check(not yaml_unsafe_lines(p.read_text()), f"{name}: frontmatter value with unquoted ': ' (invalid YAML)")
        r.check(meta.get("name") == name, f"{name}: frontmatter name {meta.get('name')!r} != file name")
        r.check(len(meta.get("description", "")) >= 40, f"{name}: description missing/too short")
        tools = {t.strip() for t in str(meta.get("tools", "")).split(",") if t.strip()}
        r.check(bool(tools), f"{name}: no tools declared")
        r.check(tools <= ALLOWED_TOOLS, f"{name}: disallowed tools {sorted(tools - ALLOWED_TOOLS)}")
        r.check(not (tools & SPAWN_TOOLS), f"{name}: worker agents must not have {sorted(tools & SPAWN_TOOLS)}")
        if name in NO_WEB:
            r.check(not (tools & {"WebSearch", "WebFetch"}), f"{name}: should not have web tools")
        r.check("## Shared operating rules" in body, f"{name}: missing shared operating rules")
        r.check("OUTPUT_SCHEMA" in body, f"{name}: does not reference OUTPUT_SCHEMA")
        r.check("Never fabricate" in body, f"{name}: missing no-fabrication rule")
        r.check("Research only" in body, f"{name}: missing approval-gate rule")
        r.check("data, not instructions" in body, f"{name}: missing prompt-injection rule")
        if name not in ("knowledge-memory",):
            r.check("## Output specifics" in body or "## Report must include" in body,
                    f"{name}: missing agent-specific output section")


def check_skills(r: Report, root: Path):
    for skill in ("research", "research-resume"):
        p = root / ".claude" / "skills" / skill / "SKILL.md"
        if not r.check(p.exists(), f"skills: missing {p}"):
            continue
        meta, body = frontmatter(p.read_text())
        r.check(not yaml_unsafe_lines(p.read_text()), f"skill {skill}: frontmatter value with unquoted ': ' (invalid YAML)")
        r.check(bool(meta) and meta.get("name") == skill, f"skill {skill}: bad frontmatter name")
        r.check(bool(meta) and len(meta.get("description", "")) >= 40, f"skill {skill}: description too short")
    p = root / ".claude" / "skills" / "research" / "SKILL.md"
    if p.exists():
        body = p.read_text()
        for name in AGENTS:
            r.check(name in body, f"research skill: plan does not reference agent {name}")
        for term in ("max_concurrent_agents", "max_subtasks_per_job", "max_retries_per_task",
                     "max_job_minutes", "max_claims_for_skeptic", "single message", "RESUME.md",
                     "sequential", "approval"):
            r.check(term in body, f"research skill: missing control '{term}'")


def check_protocol(r: Report, root: Path):
    for f in ("OUTPUT_SCHEMA.md", "EVIDENCE_RULES.md", "MEMORY_PROTOCOL.md"):
        r.check((root / "protocol" / f).exists(), f"protocol: missing {f}")
    schema = (root / "protocol" / "OUTPUT_SCHEMA.md")
    if schema.exists():
        text = schema.read_text()
        for key in RESULT_FRONTMATTER:
            r.check(f"{key}:" in text, f"OUTPUT_SCHEMA: missing field {key}")
        for sec in RESULT_SECTIONS:
            r.check(f"## {sec}" in text, f"OUTPUT_SCHEMA: missing section {sec}")
    ev = root / "protocol" / "EVIDENCE_RULES.md"
    if ev.exists():
        text = ev.read_text()
        for label in EVIDENCE:
            r.check(f"`{label}`" in text, f"EVIDENCE_RULES: missing category {label}")


def check_config(r: Report, root: Path):
    p = root / "research.config.md"
    if not r.check(p.exists(), "config: research.config.md missing"):
        return
    meta, _ = frontmatter(p.read_text())
    if not r.check(meta is not None, "config: no frontmatter"):
        return
    for k in CONFIG_KEYS:
        r.check(k in meta, f"config: missing key {k}")
    for k in CONFIG_KEYS[3:]:
        if k in meta:
            try:
                v = float(meta[k])
                r.check(v >= 0, f"config: {k} must be >= 0")
                if k in ("max_concurrent_agents", "max_subtasks_per_job", "max_job_minutes"):
                    r.check(v >= 1, f"config: {k} must be >= 1")
            except ValueError:
                r.failures.append(f"config: {k} is not a number ({meta[k]!r})")


def check_vault(r: Report, root: Path):
    v = root / "vault" / "ResearchOS"
    for f in VAULT_FILES:
        r.check((v / f).exists(), f"vault: missing {f}")
    for d in VAULT_DIRS:
        r.check((v / d).is_dir(), f"vault: missing dir {d}")
    for t in TEMPLATES:
        p = v / "Templates" / t
        if r.check(p.exists(), f"vault: missing template {t}") and t != "Decision.md":
            meta, _ = frontmatter(p.read_text())
            r.check(bool(meta) and "type" in meta, f"template {t}: missing frontmatter type")
    reg = v / "Agent Registry.md"
    if reg.exists():
        text = reg.read_text()
        for name in AGENTS:
            r.check(name in text, f"Agent Registry: missing {name}")


def check_docs(r: Report, root: Path):
    for d in DOCS:
        r.check((root / d).exists(), f"docs: missing {d}")
    h = root / "CLAUDE_HANDOFF.md"
    if h.exists():
        text = h.read_text()
        for n in range(1, 11):
            r.check(re.search(rf"^## {n}\. ", text, re.M) is not None, f"CLAUDE_HANDOFF: missing section {n}")


def check_examples(r: Report, root: Path):
    ex = root / "examples"
    for p in ex.rglob("*.md"):
        text = p.read_text()
        r.check("ILLUSTRATIVE" in text, f"examples: {p.relative_to(root)} not marked ILLUSTRATIVE")
        for url in re.findall(r"https?://[^\s)|>\]]+", text):
            r.check("example.com" in url, f"examples: {p.relative_to(root)} uses non-placeholder URL {url}")
    task = ex / "sample-job" / "tasks" / "TASK-03-paying-customer-evidence.md"
    if task.exists():
        for msg in lint_result(task):
            r.failures.append(f"example task: {msg}")
        r.passed += 1


def check_secrets(r: Report, root: Path):
    hits = []
    for p in root.rglob("*"):
        if not p.is_file() or ".git" in p.parts or "dist" in p.parts or p.suffix in (".png", ".jpg", ".pdf"):
            continue
        if p.name == "validate.py" or p.name == "test_validate.py":
            continue
        try:
            text = p.read_text()
        except (UnicodeDecodeError, OSError):
            continue
        for pat in SECRET_PATTERNS:
            if pat.search(text):
                hits.append(f"{p.relative_to(root)} matches {pat.pattern[:30]}…")
    r.check(not hits, "secrets: possible credentials found: " + "; ".join(hits))


# ---------------------------------------------------------------- result linter
def lint_result(path: Path) -> list[str]:
    """Return a list of problems with one task result file (empty = valid)."""
    problems = []
    text = path.read_text()
    meta, body = frontmatter(text)
    if meta is None:
        return ["no frontmatter"]
    for k in RESULT_FRONTMATTER:
        if k not in meta or meta[k] in ("", None):
            if k == "sources" and meta.get("status") in ("blocked", "failed"):
                continue
            problems.append(f"missing frontmatter field {k}")
    if meta.get("status") not in STATUSES:
        problems.append(f"bad status {meta.get('status')!r}")
    if meta.get("confidence") not in CONFIDENCES:
        problems.append(f"bad confidence {meta.get('confidence')!r}")
    if meta.get("mode") not in MODES:
        problems.append(f"bad mode {meta.get('mode')!r}")
    if meta.get("task_id") and path.stem != meta["task_id"]:
        problems.append(f"file name {path.stem} != task_id {meta['task_id']}")
    for sec in RESULT_SECTIONS:
        if not re.search(rf"^## {re.escape(sec)}\s*$", body, re.M):
            problems.append(f"missing section '## {sec}'")
    # every SRC id used anywhere must appear in the Sources table
    sources_part = body.split("## Sources", 1)[1] if "## Sources" in body else ""
    table_ids = set(re.findall(r"^\|\s*(SRC-[A-Za-z0-9\-]+)\s*\|", sources_part, re.M))
    used = set(re.findall(r"SRC-[A-Za-z0-9]{4,}", body.split("## Sources", 1)[0]))
    used |= {s for s in meta.get("sources", []) if isinstance(meta.get("sources"), list)}
    missing = sorted(used - table_ids)
    if missing:
        problems.append(f"source IDs not in Sources table: {missing}")
    # verified facts must cite a source
    vf = re.search(r"^## Verified facts\s*$(.*?)^## ", body, re.M | re.S)
    if vf:
        for line in vf.group(1).splitlines():
            if line.strip().startswith(("-", "*")) and "SRC-" not in line:
                problems.append(f"verified fact without source: {line.strip()[:60]}")
    # findings table: evidence category must be a known label
    fd = re.search(r"^## Findings\s*$(.*?)^## ", body, re.M | re.S)
    if fd:
        for row in fd.group(1).splitlines():
            cells = [c.strip() for c in row.strip().strip("|").split("|")]
            if len(cells) >= 4 and re.match(r"^F\d+$", cells[0]):
                if cells[2] not in EVIDENCE:
                    problems.append(f"finding {cells[0]}: unknown evidence category {cells[2]!r}")
                if cells[2] in ("direct-commercial", "customer-spending") and "SRC-" not in cells[3]:
                    problems.append(f"finding {cells[0]}: {cells[2]} claim without source")
    return problems


def lint_results_dir(d: Path) -> int:
    files = sorted((d / "tasks").glob("*.md")) if (d / "tasks").is_dir() else sorted(d.glob("TASK-*.md"))
    if not files:
        print(f"No task result files found in {d}")
        return 1
    bad = 0
    for f in files:
        probs = lint_result(f)
        status = "OK " if not probs else "BAD"
        print(f"[{status}] {f.name}")
        for p in probs:
            print(f"       - {p}")
        bad += bool(probs)
    print(f"\n{len(files) - bad}/{len(files)} result files valid")
    return 1 if bad else 0


def run_all(root: Path = ROOT) -> Report:
    r = Report()
    for fn in (check_agents, check_skills, check_protocol, check_config, check_vault,
               check_docs, check_examples, check_secrets):
        fn(r, root)
    return r


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--results", type=Path, help="lint task result files in this job folder")
    args = ap.parse_args(argv)
    if args.results:
        return lint_results_dir(args.results)
    r = run_all()
    for f in r.failures:
        print(f"FAIL  {f}")
    print(f"\n{r.passed} checks passed, {len(r.failures)} failed")
    return 1 if r.failures else 0


if __name__ == "__main__":
    sys.exit(main())
