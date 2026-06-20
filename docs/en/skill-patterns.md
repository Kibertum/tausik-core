# Shared Skill Patterns

Common patterns used across multiple skills. Reference this instead of duplicating.

## Session Health Check
```bash
.tausik/tausik status
```
Look for the "Session: Xm active / Ym wall" line. If active is near `session_warn_threshold_minutes` (default 150) → suggest `/checkpoint`. At `session_max_minutes` (default 180) → `task start` is hard-blocked; user must `/end` or `session extend`.

## CLAUDE.md Dynamic Section Update
Replace between `<!-- DYNAMIC:START -->` and `<!-- DYNAMIC:END -->`:
```
Current State
Session: #{id} | Branch: {branch} | Version: {version}
Tasks: {done}/{total} done, {active} active, {blocked} blocked
{IF handoff: Last session: {summary}}
{IF warnings: Warnings: ...}
```
Use `.tausik/tausik update-claudemd` to regenerate this section automatically.

## Handoff JSON
```json
{"summary":"...","completed":["slug1","slug2"],"in_progress":[],
 "blocked":[],"key_files":["path1"],"dead_ends":[],"next_steps":["slug1 — reason"],
 "warnings":["..."]}
```

## Knowledge Capture (on task done)
On `task done`, the agent should record meaningful learnings via `tausik decide`, `tausik dead-end`, or `tausik memory add`. SENAR Rule 8 enforces this as a warning unless the task is closed with `--no-knowledge`.
