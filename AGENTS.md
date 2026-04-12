# AGENTS.md — AI Agent Onboarding

**You are an AI agent working on a project that uses TAUSIK.**
This document tells you what TAUSIK is, why it exists, and how to work with it.

## What is TAUSIK?

TAUSIK (**T**ask **A**gent **U**nified **S**upervision, **I**nspection & **K**nowledge) is an engineering governance framework for AI agents. It enforces a disciplined workflow so you don't skip planning, lose context between sessions, or close tasks without evidence.

TAUSIK implements [SENAR v1.3 Core](https://senar.tech) ([GitHub](https://github.com/Kibertum/SENAR)) — an open methodology for AI-native development. SENAR defines:
- **Quality gates** — hard blocks that prevent skipping steps (no code without a task, no completion without evidence)
- **Workflow rules** — task lifecycle, session management, checkpoints, dead end tracking
- **Metrics** — throughput, first-pass success rate, defect escape rate, lead time (all automatic)

**Why this matters to you:** Without TAUSIK, you might hallucinate completion, repeat failed approaches, or lose context. With TAUSIK, every piece of work has a goal, acceptance criteria, and verification evidence — making your output predictable and auditable.

## Your First 60 Seconds

After bootstrap, you have these tools available:

**MCP tools** (preferred — 80 tools via `tausik-project` server):
```
tausik_status              — see project state
tausik_task_quick          — create a task
tausik_task_start          — begin work (QG-0: goal + AC required)
tausik_task_done           — complete work (QG-2: evidence required)
tausik_task_log            — log progress
tausik_memory_search       — search project knowledge
```

**CLI** (fallback):
```bash
.tausik/tausik status
.tausik/tausik task start <slug>
.tausik/tausik task done <slug> --ac-verified
```

**Skills** (slash commands — if your IDE supports them):
```
/start    — open session, load context
/plan     — create a task with goal + acceptance criteria
/ship     — review + test + commit in one step
/end      — save context, close session
```

## The Rules You Must Follow

1. **No code without a task.** Always create a task (`tausik_task_quick` or `/plan`) before writing code.
2. **QG-0: Define before you start.** Every task needs a goal and acceptance criteria before `task start`. No exceptions.
3. **QG-2: Prove before you close.** Log AC verification evidence via `task log`, then `task done --ac-verified`. No shortcuts.
4. **Log your progress.** Use `tausik_task_log` after each significant step.
5. **Document dead ends.** Failed approach? `tausik_dead_end "what" "why"` — so the next session doesn't repeat it.
6. **Session limit: 180 minutes.** Use `/checkpoint` to save progress. Use `/end` to close properly.
7. **Ask before committing.** Never `git commit` or `git push` without user confirmation.
8. **MCP-first.** Prefer MCP tools over CLI bash commands.

## Work Cycle

```
Session start    →  /start (or tausik_session_start)
Plan a task      →  /plan (or tausik_task_quick + tausik_task_update for AC)
Start task       →  tausik_task_start (QG-0 enforced)
  Work           →  code, test, log progress
  Hit dead end?  →  tausik_dead_end "approach" "reason"
Complete task    →  tausik_task_log "AC: 1. ✓ 2. ✓" → tausik_task_done (QG-2)
Ship             →  /ship (review + gates + commit)
End session      →  /end (handoff saved for next session)
```

## Documentation Map

| Need | Go to |
|------|-------|
| **Quick start for agents** | [references/QUICKSTART.en.md](references/QUICKSTART.en.md) (EN) / [references/QUICKSTART.md](references/QUICKSTART.md) (RU) |
| **CLI command reference** | [references/project-cli.md](references/project-cli.md) |
| **Architecture & internals** | [references/architecture.en.md](references/architecture.en.md) (EN) / [references/architecture.md](references/architecture.md) (RU) |
| **MCP tools (80 tools)** | [docs/en/mcp.md](docs/en/mcp.md) |
| **Skills reference (34 skills)** | [docs/en/skills.md](docs/en/skills.md) |
| **Quality gates** | [docs/en/hooks.md](docs/en/hooks.md) |
| **User-facing docs index** | [docs/README.md](docs/README.md) |
| **SENAR compliance matrix** | [docs/en/senar-compliance-matrix.md](docs/en/senar-compliance-matrix.md) |

## Repository Structure

```
scripts/           Core Python (CLI → Service → Backend)
references/        Agent-facing technical docs
agents/            Shared resources for all IDEs
  skills/          34 skill definitions (SKILL.md)
  roles/           5 role profiles (developer, architect, qa, tech-writer, ui-ux)
  stacks/          20 stack guides (python, react, go, rust, ...)
  overrides/       IDE-specific overrides (claude/, cursor/, qwen/)
  claude/mcp/      MCP servers (project: 80 tools, RAG: 7 tools)
bootstrap/         One-command project setup
tests/             pytest suite (918 tests)
docs/              User documentation (EN + RU, 13 files each)
.tausik/           Runtime data (DB, config) — gitignored
```

## Key Entry Points (for framework contributors)

| What you want | Where to look |
|---------------|---------------|
| Run a CLI command | `scripts/project.py` → dispatches to handlers |
| Business logic | `scripts/project_service.py` + `scripts/service_task.py` |
| Database schema | `scripts/backend_schema.py` |
| Quality gates config | `scripts/project_config.py` |
| Gate runner | `scripts/gate_runner.py` |
| MCP server | `agents/claude/mcp/project/server.py` |
| Bootstrap logic | `bootstrap/bootstrap.py` |
| Add a skill | `agents/skills/<name>/SKILL.md` |

## How Things Connect

```
User message → Skill (SKILL.md) → MCP tool or CLI
                                 → project_service.py (business logic)
                                 → project_backend.py (SQLite + FTS5)
                                 → gate_runner.py (quality checks)
```

Three layers, strict separation: **CLI never touches DB. Service validates. Backend executes.**
