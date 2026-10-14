---
type: config
# Where the Obsidian vault lives. Relative paths are from the repo root.
# Point this at your real vault (for example /Users/you/Obsidian/Brain) to use your existing notes.
vault_path: ./vault
# Folder inside the vault this system owns and writes to.
system_folder: ResearchOS
# Vault-relative folders holding your existing knowledge (48 Laws, psychology, sales, etc.).
# Agents read these and never write to them. Add your real folder names.
knowledge_dirs: [Knowledge]
# ---- Limits (the orchestrator must respect these) ----
max_concurrent_agents: 4        # subagents launched at the same time
max_subtasks_per_job: 12        # total agent tasks in one job, including retries
max_retries_per_task: 1         # one retry after a failed or invalid result, then mark failed
max_web_searches_per_agent: 8   # per task
max_job_minutes: 45             # stop launching new tasks after this; save state and write RESUME.md
max_candidates_wide: 8          # candidates carried forward from discovery
max_candidates_deep: 3          # candidates that get per-candidate deep tasks
max_claims_for_skeptic: 20      # claims sent to the Skeptic per job
reuse_days: 30                  # research younger than this is reused instead of redone
# ---- Spending ----
research_spend_limit_usd: 0     # paid tools, data or subscriptions: 0 means never, without explicit human approval
---

# Research System Configuration

Change the values in the frontmatter above. Every agent and the orchestrator read this file at the start of each job.

- To use your existing Obsidian brain, set `vault_path` to its absolute path and list your knowledge folders in `knowledge_dirs`. The system creates `ResearchOS/` inside your vault on first run, copied from `vault/ResearchOS/` in this repo.
- Model usage is billed by whichever Claude product runs the agents (a Claude subscription or API usage). This system calls no paid services itself.
- No secrets belong in this file. See `SECURITY.md`.
