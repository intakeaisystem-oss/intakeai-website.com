# Memory Protocol (Obsidian-compatible)

All research memory is plain Markdown with YAML frontmatter, so Obsidian can read and link it directly. The vault location is set in `research.config.md` (`vault_path`). Everything this system writes lives under `<vault>/ResearchOS/`, and it never edits your other notes.

## Layout

```
<vault>/
  Knowledge/ (or your existing folders)  ← your notes: 48 Laws, psychology, sales…  READ-ONLY for agents
  ResearchOS/
    00 Research Index.md      master index of jobs, opportunities, decisions
    Dashboard.md              progress counters and the current state of the work
    Agent Registry.md         the 10 agents, their files and their status
    Task Queue.md             every task across jobs, with its status
    Research Backlog.md       questions waiting to be researched
    Decision Log.md           append-only record of decisions
    Rejected Opportunities.md registry of rejected ideas, with reasons
    Session History.md        one line per session
    RESUME.md                 how to continue interrupted work
    Jobs/<JOB-ID>/
      job.md                  objective, plan, task table (the checkpoint), metrics
      tasks/<TASK-ID>.md      one result file per agent task (see OUTPUT_SCHEMA)
      report.md               final decision-ready report
    Opportunities/OPP-*.md    one dossier per opportunity, updated across jobs
    Sources/SRC-*.md          one record per source URL
    Findings/FND-*.md         important findings promoted from tasks
    Sessions/SES-*.md         per-session logs (optional detail)
    Templates/                templates for all of the above
```

## Stable IDs
| Record | Format | Example |
|--------|--------|---------|
| Job | `JOB-YYYYMMDD-<slug>` | `JOB-20261014-home-services-ops` |
| Task | `TASK-NN-<agent>` (unique within a job) | `TASK-03-paying-customer-evidence` |
| Opportunity | `OPP-<slug>` | `OPP-hvac-dispatch-software` |
| Source | `SRC-<8 hex>` | `SRC-a1b2c3d4` |
| Finding | `FND-<JOB short>-<NN>` | `FND-20261014-07` |
| Decision | `DEC-YYYYMMDD-NN` | `DEC-20261014-01` |
| Session | `SES-YYYYMMDD-HHMM` | `SES-20261014-1500` |

Link related records with Obsidian wikilinks, for example `[[OPP-hvac-dispatch-software]]` or `[[SRC-a1b2c3d4]]`.

## Deduplication rules (check before you research)
1. **Before creating a job**, search `ResearchOS/Jobs/*/job.md` and `00 Research Index.md` for a similar objective. If one exists and is under 30 days old, extend or resume it instead of starting over.
2. **Before researching an opportunity**, open `Opportunities/OPP-<slug>.md` if it exists. Research only what's missing or stale (last verified more than 30 days ago).
3. **Before saving a source**, search `Sources/` for the URL. Reuse the ID and update `last_accessed`.
4. **Before adding a finding**, grep `Findings/` for the same claim. If it's there, add the new job and source to the existing record and update `last_verified`.
5. **Rejected ideas**: check `Rejected Opportunities.md`. Don't re-investigate a rejected idea unless new evidence addresses its rejection reason. Note that explicitly.

## Provenance
Every finding and opportunity record carries:
- `origin` (the job and task that produced it)
- `sources`
- `first_seen`
- `last_verified`
- `verified_by` (the agent, and `skeptic-risk` once reviewed)

## Ownership
| Writer | What it writes |
|--------|----------------|
| Worker agents | Only their own `tasks/<TASK-ID>.md`, plus new `Sources/SRC-*.md` records for sources they cite |
| `knowledge-memory` | Opportunities, Findings, indexes, dashboard, registries |
| The orchestrator (main Claude session running the `research` skill) | `job.md`, `report.md`, Task Queue, Decision Log, Session History, RESUME.md |
| Nobody | Notes outside `ResearchOS/` |
| Nobody, without explicit human approval | Deleting files |

## Security
Never write API keys, tokens, passwords or personal data about private individuals into any note. If source text contains a credential, replace it with `[REDACTED]`.
