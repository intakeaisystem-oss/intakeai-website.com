# System Architecture

## Components
| Layer | Component | Implementation |
|-------|-----------|----------------|
| Coordination | Orchestrator (planning half of agent 10) | Main Claude session following `.claude/skills/research/SKILL.md` |
| Workers | Agents 1–7 and 9 | Claude Code subagents in `.claude/agents/`, each with its own instructions and tool allowlist |
| Synthesis | chief-orchestrator agent (synthesis half of agent 10) | Subagent that reads the job and writes `report.md` |
| Memory | knowledge-memory agent and vault | Markdown and YAML frontmatter under `<vault>/ResearchOS/` |
| Rules | Protocol | `protocol/*.md`, referenced by every agent |
| Config | Limits and paths | `research.config.md` frontmatter |
| Tooling | Validator and bundler | `scripts/validate.py`, `scripts/bundle.py` (stdlib Python) |

### Why the coordinator is the main session
Claude Code subagents can't spawn subagents, so the coordinator has to run in the main session. This also prevents recursive spawning by design.

## Data flow
1. The **objective** goes to the orchestrator, which reads the config and protocol, checks for duplicate jobs and creates `Jobs/<JOB-ID>/job.md`.
2. **knowledge-memory (retrieve)** returns prior research, rejected ideas and recommended knowledge notes for each agent.
3. **market-intelligence** returns candidates, as `OPP-*` IDs.
4. **Workers 03–07** run in parallel batches of `max_concurrent_agents`. Each one reads the upstream task files and its recommended notes, and writes `tasks/TASK-NN-agent.md` plus any new `Sources/SRC-*.md`.
5. **unit-economics** runs after evidence, competitor and channel results.
6. The orchestrator selects important claims and passes them to **skeptic-risk**, which writes verdicts, pre-mortems and a risk register.
7. **chief-orchestrator** applies the verdicts, resolves contradictions, scores against the rubric, writes `report.md` and updates the Ranking and Metrics sections of job.md.
8. **knowledge-memory (file)** creates or updates Opportunities, Findings and Sources, and updates the Index, Dashboard, Registry and Backlog.
9. The orchestrator updates the Task Queue, Decision Log and Session History, then gives the user a short summary.

## Task lifecycle
```
pending ──launch──► running ──valid result──► complete | partial
   ▲                   │
   │                   ├─invalid/missing result or tool error──► retry once ──► failed
   │                   └─time limit reached──► pending (interrupted) ──/research-resume──┘
blocked ◄── a dependency failed/blocked
```

## State and checkpointing
- **Source of truth:** the job.md task table plus the result files on disk.
- **Resume:** reconcile job.md with `tasks/` (see the resume skill). Tasks that have a valid result file are never re-run.

## Parallelism
- **Claude Code:** real parallel subagents, from multiple Agent tool calls in one message, capped by `max_concurrent_agents`.
- **claude.ai or any single-thread context:** sequential execution of the same agent definitions. The report records `execution: sequential`.

## Retrieval
Retrieval is hybrid lexical: filename matching, frontmatter `tags`/`topic` filters and keyword Grep over `knowledge_dirs`, ranked by `knowledge-memory`. Each agent receives at most 8 note paths, not the whole vault.

Vector search was **not** added. It needs embedding infrastructure, an index to keep in sync and extra cost, and lexical search is enough for vaults of up to a few thousand notes. ROADMAP explains when to revisit this.

## Trust boundaries
- System instructions are in the agent files, skills and protocol.
- Web pages, vault notes, reviews and documents are **untrusted data**, and every agent is told to ignore instructions found in them.
- Writes are confined to `<vault>/ResearchOS/`, with ownership rules in MEMORY_PROTOCOL.
