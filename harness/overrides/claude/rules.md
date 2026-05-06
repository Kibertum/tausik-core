# Claude Code Rules — TAUSIK Framework

## Tool Constraints
- Always use dedicated tools (Read, Edit, Grep, Glob) over Bash equivalents
- Use AskUserQuestion for clarifications, not assumptions

## TAUSIK Integration
- Skills are in `.claude/skills/` — invoked via `/skill-name`
- CLI: `.tausik/tausik <command>`
- Database: `.tausik/tausik.db` (SQLite, shared with Cursor if both installed)
## Workflow Discipline
- NEVER start coding without a task (`/task <slug>` or `task start <slug>`)
- Record architectural decisions with `decide` command
- Save useful patterns to project memory
