# Testing

## Commands (stdlib Python 3.9+; no installs)
```bash
python3 scripts/validate.py                            # structural validation of the whole system
python3 scripts/validate.py --results vault/ResearchOS/Jobs/<JOB-ID>   # lint a job's task result files
python3 scripts/test_validate.py                       # unit tests for the validator, linter and bundler
python3 scripts/bundle.py                              # build the claude.ai Project bundle in dist/
```

## What is tested (deterministic, offline)
| Area | How |
|------|-----|
| Agent instruction loading | All 10 agent files exist, frontmatter parses and is YAML-safe, `name` matches the file, descriptions and tools are present |
| Permissions | Tools ⊆ allowlist; no worker has Agent, Task or Bash (no spawning); memory and chief agents have no web tools |
| Safety rules present | Every agent has the no-fabrication, approval-gate, prompt-injection and OUTPUT_SCHEMA rules |
| Orchestration controls | The research skill references all agents and every limit, parallel launch, sequential fallback, RESUME and approval |
| Structured output | OUTPUT_SCHEMA contains every required field and section; the result linter enforces them on task files |
| Source attribution | The linter checks that every SRC ID used appears in the Sources table, verified facts cite sources, and spending claims cite sources |
| Config | Required keys are present and limits are numeric and sane |
| Memory skeleton | All registries, dirs and templates exist, and the Agent Registry lists all agents |
| Credential redaction | The secret scan covers the repo and vault (API keys, GitHub, AWS and Slack tokens, `KEY=value`) |
| Examples | Marked ILLUSTRATIVE, and only `example.com` URLs |
| Negative tests | 18 tests break things on purpose and confirm the validator or linter catches them |

## What is NOT tested (and why)
- **Live agent behaviour.** That includes whether agents follow instructions, the quality of their research, real parallel execution, retries, resume and duplicate detection in practice. These are executed by Claude at runtime. No live job has been run yet. **ROADMAP #1** is to run one and review the output with `--results`.
- **Limit enforcement.** Limits are instructions, not code. A code-level runner (ROADMAP #3) would make them testable.

## Manual acceptance test (first live run)
1. Set `max_subtasks_per_job: 8` and `max_web_searches_per_agent: 4`.
2. Run `/research deep <a small, specific idea>`.
3. Check:
   - job.md statuses
   - `python3 scripts/validate.py --results <job dir>` passes
   - each cited URL opens and supports its claim
   - the Skeptic file exists
   - report.md counts are consistent
4. Interrupt a second job mid-run, then run `/research-resume`. Completed tasks must not re-run.
5. Run the same objective again. The duplicate check should offer to extend the first job.
