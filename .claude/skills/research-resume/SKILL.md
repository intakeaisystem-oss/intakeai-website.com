---
name: research-resume
description: Resume an interrupted or partial research job from its vault checkpoint (job.md task table), or show the status of research jobs. Use when the user says "resume", "continue the research", "what's the status", or a job was interrupted.
---

# Resume / Status

1. Read `research.config.md` to find the vault `<V>`. Read `<V>/ResearchOS/RESUME.md` if it exists.
2. If no JOB-ID was given, list the jobs in `<V>/ResearchOS/Jobs/*/job.md` with status `running`, `interrupted` or `partial`, newest first. Show each job's ID, objective and task counts by status. If the user only asked for status, stop here.
3. For the chosen job, open `job.md` and its `tasks/` folder. Reconcile the two:
   - A task marked `running` with **no** result file goes back to `pending` (it was interrupted).
   - A task marked `running` or `pending` with a **valid** result file takes the status in that file's frontmatter. This avoids redoing finished work.
   - A task marked `failed` stays failed unless the user asks to retry. It still counts toward `max_subtasks_per_job`.
4. Count the work already done against `max_subtasks_per_job`. If no budget is left, tell the user and ask before raising the limit.
5. Continue with step 3 (Execute) of `.claude/skills/research/SKILL.md`, using the same JOB-ID.
6. When the job finishes, clear `RESUME.md`, keeping only the heading and "No interrupted jobs".

## Writing RESUME.md (when a job stops early)
```markdown
# Resume instructions
- Job: [[JOB-…]] — <objective>
- Stopped at: <timestamp>
- Reason: time limit | user stop | error | subtask budget
- Completed: TASK-01, TASK-02 …
- Pending/interrupted: TASK-05 (interrupted), …
- Next action: run `/research-resume JOB-…`
```
