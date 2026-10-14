# Operations Guide

## Running a research job (Claude Code)
| Goal | Command |
|------|---------|
| Wide discovery | `/research Find recurring-revenue service businesses for independent dental practices` |
| Deep dive on one idea | `/research deep Mobile pressure-washing subscription for HOA communities in Phoenix` |
| Deep dive on an existing record | `/research deep OPP-hvac-dispatch-software` |
| Add constraints | `/research Opportunities I can start part-time, < $5k capital, UK, no software dev` |
| Check status | `/research-resume` (lists jobs and their state) |
| Resume a job | `/research-resume JOB-20261014-home-services-ops` |

Without slash commands, say: "Follow `.claude/skills/research/SKILL.md` for: <objective>".

### What you get
- `Jobs/<JOB-ID>/report.md`: ranking, counts, top candidates, Skeptic challenges, and next steps.
- `Jobs/<JOB-ID>/tasks/*.md`: each agent's full structured output.
- New or updated `Opportunities/`, `Findings/` and `Sources/` records, plus an updated Index and Dashboard.

### Good practice
- Start with low limits for the first run, for example `max_subtasks_per_job: 8` and `max_web_searches_per_agent: 5`.
- Read the Skeptic's task file before acting on a recommendation.
- Record your own decisions with "log decision: …". The orchestrator appends them to `Decision Log.md`.
- Re-run deep jobs on promising candidates instead of one huge wide job.

## Running a single agent
Ask: "Use the competitor-intelligence agent on OPP-x for job JOB-…, task TASK-12-competitor-intelligence". If no job exists yet, the orchestrator creates one, so results are still filed.

## claude.ai (Projects) usage
1. Run `python3 scripts/bundle.py` to create:
   - `dist/PROJECT_KNOWLEDGE.md`: all agents, the protocol, the config and the templates in one file
   - `dist/PROJECT_INSTRUCTIONS.md`
2. Create a Project. Paste PROJECT_INSTRUCTIONS into the custom instructions and upload PROJECT_KNOWLEDGE, plus any of your vault notes you want used.
3. Ask: "Run a research job: <objective>".

   Claude plays each agent role in order. It produces each task result as a Markdown block, then the report. Copy them into your vault under `ResearchOS/Jobs/<JOB-ID>/`.
4. Limits:
   - Execution is sequential, not parallel.
   - There's no direct vault access, so saving is manual.
   - Web research depends on web search being enabled in your claude.ai settings.

## Inspecting and maintaining research
- **Dashboard and Index:** start there in Obsidian.
- **Stale records:** Grep for `last_verified:` older than `reuse_days`, or ask "list opportunities needing re-verification".
- **Rejections:** add them with "reject OPP-x because …". knowledge-memory records the reason and the revisit conditions.
- **Never delete records.** Mark them `status: merged` or `rejected` instead.

## Troubleshooting
| Symptom | Fix |
|---------|-----|
| Agent didn't write a result file | The orchestrator retries once, then marks it failed. Re-run with `/research-resume` |
| `mode: offline` in results | Web tools weren't available. Enable WebSearch/WebFetch, then re-run the affected tasks |
| Duplicate opportunity records | Ask knowledge-memory to merge them (it keeps the older ID) |
| Job hit the time limit | `/research-resume <JOB-ID>` |
| Agents not found by `/agents` | Run Claude Code from the repo root, so `.claude/` is picked up |
