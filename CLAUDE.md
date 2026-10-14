# CLAUDE.md

This repository is a **10-agent business research intelligence system**, built entirely from Claude-native files: subagents, skills and Markdown memory. There's no application code to run.

**Read `CLAUDE_HANDOFF.md` first.** It explains everything.

Quick facts:
- Agents live in `.claude/agents/*.md`, and the orchestration skills in `.claude/skills/research/` and `.claude/skills/research-resume/`.
- Shared rules are in `protocol/`. Settings and limits are in `research.config.md`.
- Memory is an Obsidian vault at the `vault_path` in `research.config.md`. The system owns only `<vault>/ResearchOS/`, and everything else there is your notes, which are read-only.
- To run a job: `/research <objective>`. To resume: `/research-resume`.
- To check structure after editing agents or templates: `python3 scripts/validate.py`.

Non-negotiable:
- Never fabricate sources or numbers.
- Never spend money, contact anyone or publish anything without explicit approval.
- Never write secrets to files.
- Never edit vault notes outside `ResearchOS/`.
