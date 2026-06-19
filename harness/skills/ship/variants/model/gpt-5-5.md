<!-- /ship — GPT-5.5 overlay (telegraphic delta, not a rewrite) -->

## GPT-5.5 model quirks

- **Maximum parallelism.** Run review subagent + full gate sweep (ruff + mypy + filesize + scoped pytest) in one parallel batch.
- Auto-compose commit message from `task_log` entries of last completed task (or all tasks if batched). Subject = task title; body = bullet-list of `task_log` highlights + AC verification summary.
- **Zero filler.** "Commit ready: <subject>" — present, await user OK, commit. No multi-paragraph rationale.
- Single-turn commit: present message + invoke `git commit` in same turn (with explicit user-confirmation gate via `AskUserQuestion` if non-interactive policy).
- For batched commits: one `git commit` for all related changes; don't fragment into N commits unless user asks.
- Never push without explicit user request — surface a "next: git push? (y/N)" prompt instead of acting.
- Heredoc commit messages always.
- After commit: one-line confirmation with SHA short hash, nothing else.
