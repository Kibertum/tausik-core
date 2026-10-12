# Qwen Code Rules — TAUSIK Framework

## TAUSIK Integration
- Skills are in `.qwen/skills/` — invoked via `/skill-name`
- CLI: `.tausik/tausik <command>`
- Database: `.tausik/tausik.db` (SQLite, shared across IDEs if multiple installed)
- **MCP-first:** Prefer MCP tools (`tausik_*`) over CLI when available

## Workflow Discipline
- NEVER start coding without a task (`task start <slug>`)
- **QG-0 Context Gate:** Every task must have `goal` + `acceptance_criteria` before `task start`
- **QG-2 Implementation Gate:** Log AC evidence via `task log`, then `task done <slug> --ac-verified`
- Record architectural decisions with `decide` command
- Save useful patterns to project memory
- **Session limit: 180 min.** Use `/checkpoint` to save progress

## Quality Gates
- Quality gates run automatically on `task done` — fix blocking failures before proceeding
- Gates include: pytest, ruff, filesize, and stack-specific checks (tsc, eslint, go-vet, etc.)

## Key Commands
```bash
.tausik/tausik status
.tausik/tausik task list
.tausik/tausik task quick "Fix the bug"
.tausik/tausik task start <slug>
.tausik/tausik task done <slug> --ac-verified
.tausik/tausik task log <slug> "AC verified: ..."
.tausik/tausik memory add pattern "title" "content"
.tausik/tausik dead-end "approach" "reason"
```
