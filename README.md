# Marketing & Research Intelligence for Claude

This repository has two systems:

1. **Marketing, Sales, Advertising & Conversion Toolkit** (`marketing_toolkit/`). This is working Python code: customer psychology, voice-of-customer analysis, offer scoring, copy evaluation, ad concepts, funnel and landing-page audits, metrics, A/B statistics, sales and objection handling, reusable components, persistent memory, and import-ready packages for normal Claude. See **`MARKETING_TOOLKIT.md`**. The ready-to-upload packages are in **`claude_packages/`**.
2. **Business Research Intelligence System** (10 Claude agents), described below.

---

# Business Research Intelligence System (10 agents)

This is a modular, persistent research system made of **10 specialist Claude agents**. It finds, evidences, challenges and ranks business opportunities of any kind: online or offline, B2B services, software, e-commerce, productized services and recurring-revenue models. All research is stored in an **Obsidian-compatible vault**.

It's built from Claude-native files, so Claude imports and runs it directly:

| Piece | Location |
|-------|----------|
| 10 agent definitions (Claude Code subagents) | `.claude/agents/` |
| Orchestrator (planning, delegation, tracking, retries, resume) | `.claude/skills/research/` and `.claude/skills/research-resume/` |
| Shared rules (output schema, evidence rules, memory protocol) | `protocol/` |
| Settings and limits | `research.config.md` |
| Memory skeleton (index, registries, queue, templates) | `vault/ResearchOS/` |
| Handoff docs | `CLAUDE_HANDOFF.md` (start here), plus the other `*.md` files at the root |

## Quick start

### Claude Code (full system, with parallel subagents)
```bash
git clone <this repo> && cd <repo>
# optional: point research.config.md -> vault_path at your real Obsidian vault
claude
> /research Find underserved B2B service opportunities in home services I could start with under $10k
```

Results land in `vault/ResearchOS/Jobs/<JOB-ID>/report.md`, or under your vault if you changed `vault_path`.

### claude.ai (Projects)
1. Run `python3 scripts/bundle.py` to generate `dist/PROJECT_KNOWLEDGE.md`.
2. Upload that file to a Claude Project's knowledge, and paste `dist/PROJECT_INSTRUCTIONS.md` into the project instructions.
3. Ask: "Run a research job: <objective>".

In claude.ai, the agents run as **sequential roles in one conversation**, not as parallel subagents. Results come back as Markdown for you to save into your vault.

## What it is not
- It doesn't launch businesses, contact prospects, buy anything or run ads. Those actions require your explicit approval.
- A generated idea isn't a validated business. Reports count ideas, screened candidates and evidence-supported opportunities separately.

See `CLAUDE_HANDOFF.md` for the full picture.
