**English** | [Русский](README.ru.md)

# TAUSIK

**AI development framework — plan, build, ship with quality control.**

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB.svg)](https://python.org)
[![Tests](https://github.com/Kibertum/tausik-core/actions/workflows/tests.yml/badge.svg)](https://github.com/Kibertum/tausik-core/actions/workflows/tests.yml)
[![2270 tests](https://img.shields.io/badge/tests-2270%20passed-brightgreen.svg)](#dogfooding-tausik-built-tausik)
[![Zero deps](https://img.shields.io/badge/dependencies-0-brightgreen.svg)](#what-you-get)

Three messages. Full engineering cycle. Quality gates that the agent can't skip.

> Works with Claude Code, Cursor, Qwen Code (GigaCode), Windsurf.

## Try It Now

Tell your AI agent:

```
Add https://github.com/Kibertum/tausik-core as a git submodule in .tausik-lib,
run python .tausik-lib/bootstrap/bootstrap.py --init,
add .tausik/ to .gitignore
```

The agent will execute all three steps. Restart your IDE after — done.

Then just three messages:

```
start working
```
```
fix the bug — button doesn't work on mobile
```
```
ship it
```

That's it. The agent opens a session, creates a task with acceptance criteria, writes the code, runs tests and code review, verifies each criterion with evidence, commits, and offers to push. Full engineering cycle — you just describe what you want.

## What You Get

| Without TAUSIK | With TAUSIK |
|---|---|
| Agent starts coding immediately | Must define goal + acceptance criteria first |
| Claims "done" without proof | Completion blocked until every criterion has evidence |
| Context lost between sessions | Decisions, patterns, and dead ends persist across sessions |
| Same mistake repeated 3 times | Failed approaches recorded — agent sees what didn't work |
| No tests, no linting | 25 checks auto-run for your stack (pytest, ruff, tsc, eslint, cargo, go vet...) |
| No visibility into process | 6 metrics tracked automatically — throughput, defect rate, lead time |

**The key difference:** TAUSIK quality gates are _enforcement_. The agent physically cannot skip steps — no prompts, no hoping, no "please remember to run tests."

## Manual Quick Start

If you prefer to set things up yourself:

```bash
cd your-project
git submodule add https://github.com/Kibertum/tausik-core .tausik-lib
python .tausik-lib/bootstrap/bootstrap.py --init
```

Bootstrap auto-detects your tech stack and enables matching quality gates. Project name is derived from the directory.

> After bootstrap, restart your IDE so MCP servers load. Without a restart the agent falls back to CLI mode.

**[Detailed quick start guide ->](docs/en/quickstart.md)**

## How It Works

**Plan before code.** `/plan` starts with an interview — the agent asks clarifying questions about behavior, edge cases, and constraints. Then it creates tasks with acceptance criteria. No coding until the goal is defined.

**Ship with confidence.** `/ship` runs code review (5 parallel agents), tests, verifies each acceptance criterion, commits, and suggests updating docs. One command — full quality pipeline.

**Remember everything.** Decisions, patterns, conventions, and failed approaches are stored in a local SQLite database with full-text search. New session? The agent picks up right where you left off.

**Enforce, not suggest.** Quality gates block the agent at two checkpoints: QG-0 (can't start without goal + criteria) and QG-2 (can't close without evidence + passing tests). Hooks block code edits without a task and dangerous shell commands in real time.

## Anti-Drift (v1.3)

Agents in long sessions "drift" — ignore the framework, skip task creation, forget conventions. TAUSIK 1.3 adds real-time drift guards:

- **SessionStart hook** auto-injects state (active tasks, Memory Block, conventions) into every new session — no manual `/start`.
- **UserPromptSubmit hook** detects coding-intent phrases (EN+RU) and nudges the agent if no task is active.
- **Stop hook keyword detector** catches "I'll implement" / "сейчас напишу" announcements and blocks the stop if no task exists.
- **PostToolUse verify-fix-loop** audits every `task_done` against 5 rule-based checks (file paths, ✓ markers, test counts, file refs, lint status).
- **Memory Block re-injection** — recent decisions + conventions + dead ends pushed back into context on `/start` and `/checkpoint`.
- **Adversarial critic** — 6th parallel `/review` agent finds 3 weaknesses the others miss.

Plus: `/interview` (Socratic Q&A before complex tasks), `tausik hud` (one-screen live dashboard), `tausik suggest-model` (Haiku/Sonnet/Opus routing), webhook notifications (Slack/Discord/Telegram).

## Memory Discipline (v1.3.0)

Claude's auto-memory (`~/.claude/projects/*/memory/`) is cross-project — anything project-specific written there leaks context between unrelated repos. TAUSIK 1.3 keeps the two stores separate:

- **PreToolUse block** — any Write/Edit/MultiEdit under `~/.claude/projects/*/memory/` from a TAUSIK project is blocked with a guidance message; genuine cross-project preferences bypass via the `confirm: cross-project` marker in the user's latest prompt.
- **PostToolUse audit** — after every auto-memory write the file is scanned for project markers (absolute paths, kebab slugs, `.tausik/tausik` commands, source-file refs); matches produce a stderr warning so bypasses that still carry project traces don't slip through.
- **Policy rule in Memory Block** — every session-start injection begins with an explicit rule on where project knowledge belongs.

## Shared Brain (optional, in progress)

A second, **cross-project** knowledge layer backed by Notion. Local `.tausik/tausik.db` keeps project-specific traces; the shared brain keeps only knowledge that's generalizable (architectural decisions, patterns, gotchas, web cache). Modules shipped: stdlib-only Notion REST client (throttle + retry + pagination), local SQLite FTS5 mirror with `unicode61` tokenizer, delta pull-sync, bm25-ranked search. 102/102 new tests passing, zero external deps. Privacy preserved via `SHA256(project_name)[:16]` hashes — no plaintext project names leave the machine.

Still pending: MCP tools, init wizard, scrubbing linter, classifier. See **[Shared Brain docs ->](docs/en/shared-brain.md)** for setup and architecture.

## What's Inside

- **13 core skills** (always deployed) — `/start`, `/end`, `/checkpoint`, `/plan`, `/task`, `/ship`, `/commit`, `/review`, `/test`, `/debug`, `/explore`, `/interview`, `/brain`. Plus **25+ official/vendor skills** (`/audit`, `/zero-defect`, `/markitdown`, `/docs`, `/security`, `/onboard`, …) installed on demand via `tausik skill install`.
- **96 MCP tools** (90 project + 6 brain) — full programmatic access to the project database
- **25 quality checks** — pytest, ruff, tsc, eslint, cargo check, go vet, and more for your stack
- **6 automatic metrics** — throughput, first-pass success rate, defect rate, lead time
- **Project memory** — SQLite + FTS5, graph relations, dead-end tracking, Memory Block re-injection
- **19 Claude Code hooks** — task gate, bash firewall, push gate, auto-format, activity event, SessionStart, UserPromptSubmit, Stop × 2, PostToolUse verify, memory pre-write block, memory post-write audit, brain post-WebFetch cache, brain pre-search proactive, notify-on-done, session-metrics, session-cleanup-check, task-call-counter
- **Batch execution** — `/run plan.md` executes multi-task plans autonomously
- **Zero dependencies** — Python 3.11+ stdlib only; MCP deps in isolated `.tausik/venv/`

## Supported IDEs

| IDE | MCP Tools | Skills | Hooks | Rules |
|-----|-----------|--------|-------|-------|
| Claude Code | 96 tools | 13 core + 25+ on demand | 19 hooks (task gate, bash firewall, push gate, auto-format, activity, memory guards, brain auto-cache, ...) | CLAUDE.md |
| Qwen Code | 96 tools | 13 core + 25+ on demand | 19 hooks (same as Claude) | QWEN.md |
| Cursor | 96 tools | 13 core + 25+ on demand | — | .cursorrules |
| Windsurf | 96 tools | 13 core + 25+ on demand | — | .windsurfrules |
| Codex | — | — | — | AGENTS.md only |

**Hooks** block code edits without a task, dangerous shell commands, and direct push to main — in real time. Available in Claude Code and Qwen Code. Cursor and Windsurf get the same MCP tools and skills, with quality gates at `task start` and `task done`.

## Dogfooding: TAUSIK Built TAUSIK

TAUSIK was developed using itself. Real numbers:

| Metric | Value |
|---|---|
| Tasks completed | 516 |
| Sessions | 37 |
| Throughput | ~14 tasks/session |
| Test count | 2270 |
| Dependencies | 0 core |

Every feature, every refactor, every bug fix went through the same quality gates that ship with the framework.

## Methodology

TAUSIK implements [SENAR](https://senar.tech) ([GitHub](https://github.com/Kibertum/SENAR)) — an open engineering standard for AI-assisted development. Quality gates, session management, metrics, verification checklists — it's all defined in SENAR.

**[Read more about SENAR ->](docs/en/senar.md)**

## Documentation

| Document | Description |
|----------|-------------|
| **[Quick Start](docs/en/quickstart.md)** | First setup — 10-15 minutes |
| **[What is SENAR?](docs/en/senar.md)** | The methodology behind TAUSIK |
| **[Workflow](docs/en/workflow.md)** | A typical day with TAUSIK |
| **[Skills](docs/en/skills.md)** | 13 core + 25 vendor (38 total) skills |
| **[Hooks](docs/en/hooks.md)** | Real-time enforcement |
| **[CLI Commands](docs/en/cli.md)** | Terminal command reference |
| **[MCP Tools](docs/en/mcp.md)** | 96 tools for the AI agent |
| **[Architecture](docs/en/architecture.md)** | How the framework works inside |

**[Full documentation ->](docs/README.md)**

## License

[Apache License 2.0](LICENSE)
