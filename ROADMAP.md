# Roadmap (prioritized)

| # | Improvement | Why | Effort |
|---|-------------|-----|--------|
| 1 | **Run the first real job** on a narrow objective with low limits, then tune agent instructions based on what they get wrong | Nothing has been tested end-to-end with live web research yet | Low |
| 2 | **Connect the real Obsidian vault**: set `vault_path` and `knowledge_dirs`, and tag your 48 Laws, psychology and sales notes | The sales-psychology and knowledge-memory agents get much better with your notes | Low |
| 3 | **Code-level runner** using the Claude Agent SDK, reusing these same agent files, for hard budget, token and time enforcement, unattended or scheduled runs, and cost logging | Limits are currently instruction-enforced | Medium |
| 4 | **Result-file linter.** *Done:* `scripts/validate.py --results`. *Next:* add checks for estimate labels and Skeptic coverage, and run it from a post-task hook | Makes validation deterministic | Low |
| 5 | **Scheduled re-verification** of opportunities whose `last_verified` is older than `reuse_days` | Keeps evidence fresh | Medium |
| 6 | Source archiving: save a text snapshot of key pages, because pricing pages change | Improves auditability | Medium |
| 7 | Semantic retrieval, *only if* the vault exceeds a few thousand notes and lexical search misses things. Start with a local embedding index; avoid hosted vector DBs | Better recall | Medium |
| 8 | Optional connectors (MCP), such as Google Trends, review APIs and procurement databases, added only with approval for any that cost money | Stronger evidence | Varies |
| 9 | Opportunity comparison view: an Obsidian Dataview dashboard over the `Opportunities/` frontmatter | Easier browsing | Low |
| 10 | Calibration log: track which ranked opportunities proved right or wrong later, to tune the rubric weights | Better ranking | Low, ongoing |

## Implemented vs planned
| Capability | Status |
|------------|--------|
| 10 agents, structured outputs, protocol | Implemented |
| Orchestration: plan, dependencies, parallel, retries, limits, resume | Implemented (instruction-level) |
| Skeptic claim review and risk register | Implemented |
| Obsidian memory skeleton and templates | Implemented |
| Lexical retrieval of your notes | Implemented |
| Structural validator, secret scan, claude.ai bundle | Implemented and tested |
| Live end-to-end run | Not yet done |
| Hard code-enforced limits, cost logging | Planned (#3) |
| Result-file linter (`validate.py --results`) | Implemented and tested |
| Semantic retrieval | Planned, conditional (#7) |
