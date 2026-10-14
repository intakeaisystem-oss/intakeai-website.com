# Configuration

## research.config.md (main settings)
Edit the YAML frontmatter.

| Key | Default | Meaning |
|-----|---------|---------|
| `vault_path` | `./vault` | Obsidian vault root. Set it to your real vault's absolute path |
| `system_folder` | `ResearchOS` | The folder inside the vault that this system owns |
| `knowledge_dirs` | `[Knowledge]` | Vault-relative folders holding your notes (48 Laws, psychology, sales, …), read-only |
| `max_concurrent_agents` | 4 | Subagents launched at the same time |
| `max_subtasks_per_job` | 12 | Total agent tasks per job, including retries |
| `max_retries_per_task` | 1 | Retries after a failed or invalid result |
| `max_web_searches_per_agent` | 8 | Search budget per task |
| `max_job_minutes` | 45 | After this, stop launching tasks and write RESUME.md |
| `max_candidates_wide` | 8 | Candidates carried forward from discovery |
| `max_candidates_deep` | 3 | Candidates that get per-candidate deep tasks |
| `max_claims_for_skeptic` | 20 | Claims reviewed per job |
| `reuse_days` | 30 | Freshness window for reusing research |
| `research_spend_limit_usd` | 0 | Paid data or tools. 0 means never, without explicit approval |

These limits are **enforced by Claude following the skill instructions**, not by code. To get hard enforcement, see ROADMAP item 3.

## Connecting your existing Obsidian brain
1. Set `vault_path: /absolute/path/to/YourVault`.
2. Set `knowledge_dirs` to the folders that hold your research, for example `[Books/48 Laws, Psychology, Sales, Marketing]`.
3. Optionally, add `tags:` frontmatter to your notes to improve retrieval.
4. On the first job, the orchestrator copies the `vault/ResearchOS/` skeleton into your vault. It never overwrites existing files.
5. In Claude Code, make sure the vault path is readable and writable from your session. If the vault is outside the repo, start Claude with `--add-dir /path/to/vault`.

## Claude Code settings
- **Models:** agents omit `model`, so they inherit the session model. To choose a cheaper model for workers, add `model: sonnet` (or `haiku`) to an agent's frontmatter. That's your choice; quality may drop.
- **Web tools:** agents list `WebSearch` and `WebFetch`. If your permission settings prompt for them, approve them, or allow them in `.claude/settings.json`.

## Environment variables
None are required. Claude Code uses your existing login. `.env.example` lists optional variables for a future code-based runner, as names only. **Never commit real values.**
