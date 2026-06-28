# Cursor Rules — TAUSIK Framework

## TAUSIK Integration
- Skills are in `.cursor/skills/` — reference them for structured workflows
- CLI: `.tausik/tausik <command>`
- Database: `.tausik/tausik.db` (SQLite, shared with Claude Code if both installed)

## Workflow Discipline
- NEVER start coding without a task (`task start <slug>`)
- Record architectural decisions with `decide` command
- Save useful patterns to project memory

## Key Commands
```bash
.tausik/tausik status
.tausik/tausik task list
.tausik/tausik task quick "Fix the bug"
.tausik/tausik task start <slug>
.tausik/tausik task done <slug>
.tausik/tausik memory add pattern "title" "content"
```
