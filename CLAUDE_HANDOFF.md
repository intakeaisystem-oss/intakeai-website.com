# CLAUDE_HANDOFF — read this first

You're picking up a business research system. Don't assume you remember any earlier conversation. Everything you need is in this repository.

## 1. What the system does
It takes a business research question, which can be broad ("what could I start with $10k?") or specific ("is mobile EV charger installation for apartment blocks viable in Texas?"). It then:

1. generates and screens candidate opportunities
2. finds evidence of real customer spending
3. studies competitors, channels, buyer psychology and unit economics
4. has a Skeptic challenge the important claims
5. ranks the candidates
6. saves everything as linked Markdown records in an Obsidian vault, so future work builds on past work instead of repeating it

It covers any business type. It is **research infrastructure only**: no launching, outreach, purchasing or publishing without explicit human approval.

## 2. How the 10 agents work together
```
                       ┌────────────────────────────────────┐
 user objective ─────► │ 10 Chief / Orchestrator (main      │
                       │ session running /research skill)   │
                       └──────────────┬─────────────────────┘
                                      ▼
                    01 knowledge-memory (retrieve: prior work, notes, dedupe)
                                      ▼
                    02 market-intelligence (candidates)
                                      ▼
   ┌───────────────┬──────────────────┼──────────────────┬───────────────────┐
   ▼               ▼                  ▼                  ▼                   ▼
03 paying-     04 competitor-    05 marketing-      06 sales-          07 ai-tools-
customer-      intelligence      distribution       psychology         automation
evidence                                            (uses your notes)
   └───────┬───────┴────────┬─────────┘                  │                   │
           ▼                │                            │                   │
   08 unit-economics ◄──────┘                            │                   │
           └──────────────────────┬──────────────────────┴───────────────────┘
                                  ▼
                    09 skeptic-risk (claim review, pre-mortems, risks)
                                  ▼
                    10 chief-orchestrator agent (resolve, rank, report.md)
                                  ▼
                    11 knowledge-memory (file: opportunities, findings, sources, indexes)
```
- Tasks 03–07 run **in parallel**: the orchestrator launches them in one message with multiple Agent calls, up to `max_concurrent_agents`.
- Every agent writes one structured result file (`protocol/OUTPUT_SCHEMA.md`) and returns a short summary.
- `job.md` is the checkpoint, so interrupted jobs can resume.

## 3. Where things live
| What | Where |
|------|-------|
| Agent definitions | `.claude/agents/<name>.md` (frontmatter: name, description, tools; body: instructions plus shared rules) |
| Orchestration | `.claude/skills/research/SKILL.md` (plan → execute → skeptic → synthesize → file) |
| Resume and status | `.claude/skills/research-resume/SKILL.md` |
| Rules | `protocol/OUTPUT_SCHEMA.md`, `protocol/EVIDENCE_RULES.md`, `protocol/MEMORY_PROTOCOL.md` |
| Config and limits | `research.config.md` |
| Research memory | `<vault_path>/ResearchOS/` (default `vault/ResearchOS/`) |
| The user's knowledge notes | `<vault_path>/<knowledge_dirs>` (default `vault/Knowledge/`, currently empty) |
| Examples | `examples/` (illustrative only, not real research) |
| Validator and bundler | `scripts/validate.py`, `scripts/bundle.py` |

## 4. How to run it
- **Claude Code:** `/research <objective>` (add `deep` for a single-opportunity deep dive). Resume with `/research-resume`.
- **Without the slash command:** say "Follow `.claude/skills/research/SKILL.md` for this objective: …".
- **claude.ai Projects:** see `OPERATIONS_GUIDE.md` § claude.ai. Roles run sequentially there.

## 5. How to inspect and update research
- Start at `ResearchOS/00 Research Index.md` and `Dashboard.md`.
- Each job is in `Jobs/<JOB-ID>/`: `job.md` (plan, status, metrics), `tasks/` (raw agent outputs) and `report.md`.
- Opportunity dossiers are in `Opportunities/OPP-*.md`. Update them by appending, never by deleting history.
- To re-verify an opportunity, run `/research deep OPP-<slug>`. The agents will reuse fresh evidence and re-check stale evidence.

## 6. How to add or improve an agent
1. Copy an existing file in `.claude/agents/`. Keep the frontmatter fields `name`, `description` and `tools`, and keep the **Shared operating rules** block.
2. Define its role, inputs, method and "Output specifics", which are sections in addition to OUTPUT_SCHEMA.
3. Register it in `vault/ResearchOS/Agent Registry.md` and add it to the plan table in `.claude/skills/research/SKILL.md`.
4. Run `python3 scripts/validate.py`.
5. Keep agents single-purpose, and never give a worker agent the ability to spawn agents.

## 7. How to avoid duplicating work
Follow `protocol/MEMORY_PROTOCOL.md` § Deduplication:

- The orchestrator checks for similar jobs.
- `knowledge-memory` (retrieve) lists reusable, stale and rejected records.
- Agents check Opportunities, Findings and Sources before searching.
- `knowledge-memory` (file) merges records rather than duplicating them.
- Research younger than `reuse_days` is reused.

## 8. Implemented, tested, incomplete
| Capability | State |
|------------|-------|
| 10 agent definitions with structured output | **Implemented.** Validated structurally by `scripts/validate.py` |
| Orchestration (plan, dependencies, parallel launch, status tracking, retries, limits, resume) | **Implemented** as skill instructions, executed by Claude |
| Skeptic review of selected claims | **Implemented** |
| Obsidian memory: index, registry, queue, backlog, opportunities, sources, findings, decisions, rejected, dashboard, sessions, resume | **Implemented** as skeleton and templates |
| Retrieval of the user's knowledge notes | **Implemented** as filename, tag and keyword search (Grep/Glob). No semantic or vector search |
| Cost and permission controls | **Implemented** as config limits plus hard rules. Enforced by Claude following instructions, **not** by code |
| Structural tests and result-file linter | **Implemented and run** (`scripts/validate.py`, `scripts/test_validate.py`: 21 tests) |
| End-to-end live research run | **Not yet run.** No real job has been executed. The examples are illustrative |
| Hard (code-enforced) budget/token limits | **Planned** (ROADMAP) |
| Semantic retrieval | **Planned, if the vault grows large** (ROADMAP) |
| The user's existing notes connected | **Pending.** Set `vault_path` and `knowledge_dirs` |

## 9. Continuing development safely
- Keep the rules in `protocol/` as the single source of truth. Agents reference them, so don't fork the rules into each agent.
- Never weaken the hard rules: no fabrication, no spending or outreach without approval, no secrets in files, no edits outside `ResearchOS/`, no recursive spawning.
- Run `python3 scripts/validate.py` after every edit, and keep the examples clearly marked illustrative.
- Test changes on a small objective with low limits before running big jobs.

## 10. Highest-priority next improvements
See `ROADMAP.md`. The top 5:

1. Run the first real job and fix whatever the agent outputs get wrong.
2. Connect the real Obsidian vault and tag the knowledge notes.
3. Add a code-level runner (Claude Agent SDK) for hard budget enforcement and unattended runs.
4. Extend the result-file linter (`scripts/validate.py --results`) and run it automatically after each task, from a Claude Code hook.
5. Add a scheduled re-verification pass for stale opportunities.
