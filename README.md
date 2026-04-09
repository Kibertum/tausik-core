**English** | [Русский](README.ru.md)

# TAUSIK

**Task Agent Unified Supervision, Inspection & Knowledge**

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB.svg)](https://python.org)
[![Tests](https://github.com/Kibertum/tausik-core/actions/workflows/tests.yml/badge.svg)](https://github.com/Kibertum/tausik-core/actions/workflows/tests.yml)
[![918 tests](https://img.shields.io/badge/tests-918%20passed-brightgreen.svg)](#dogfooding-tausik-built-tausik)
[![Zero deps](https://img.shields.io/badge/dependencies-0-brightgreen.svg)](#key-features)

An engineering governance framework for AI coding agents. Forces planning before code, evidence before completion, and memory across sessions.

> Your AI agent deleted production code again? TAUSIK won't let it.

**Who it's for:** developers and teams who use AI coding agents (Claude Code, Cursor, Windsurf) and want predictable, auditable results instead of hoping the agent gets it right.

## The Problem

AI coding agents are powerful, but without enforcement they:

- **Skip planning** — jump straight into code without defining what "done" means
- **Fake completion** — claim the task is done without running tests or checking acceptance criteria
- **Lose context between sessions** — start from scratch every time, repeating the same mistakes
- **Repeat failed approaches** — try the same broken solution three times because nothing tracks what already failed

AGENTS.md and .cursorrules are _recommendations_ the agent can ignore. You need _enforcement_.

## The Solution

TAUSIK sits on top of your AI IDE and enforces an engineering process — not with prompts, but with hard blocks.

| Without TAUSIK | With TAUSIK |
|---|---|
| Agent starts coding immediately | Must define goal + acceptance criteria before writing any code |
| No verification of results | Task completion blocked until every criterion has documented evidence and all checks pass |
| Context lost between sessions | Project memory persists patterns, decisions, and dead ends across sessions |
| Same mistake repeated 3 times | Failed approaches are recorded — the agent sees what didn't work |
| "Tests? What tests?" | 15 checks auto-run for your stack (pytest, ruff, tsc, eslint, cargo check, go vet...) |
| No process visibility | 6 metrics tracked automatically: throughput, first-pass success rate, defect rate, lead time, and more |

**Key difference:** TAUSIK quality gates are _enforcement_ — the CLI physically blocks the agent from skipping steps.

## Quick Start

```bash
cd your-project
git submodule add https://github.com/Kibertum/tausik-core .tausik-lib
python .tausik-lib/bootstrap/bootstrap.py --smart --init my-project
```

`--smart` auto-detects your tech stack and enables matching quality gates. `--init my-project` creates the project database (replace `my-project` with your project name).

> **Important:** After bootstrap, restart your IDE window (Claude Code, Cursor, Windsurf) so that MCP servers are loaded. Without a restart the agent will fall back to CLI mode.

Tell the agent in chat:

```
start working
```

The agent opens a session, loads project context, and shows a dashboard. Then just describe a task:

```
fix the bug — button doesn't work on mobile
```

The agent creates a task, starts working. When done — tell it `ship it`. Three messages, full engineering cycle with quality control.

**[Detailed quick start guide ->](docs/en/quickstart.md)**

## How It Works

**Task lifecycle.** Every piece of work goes through a defined lifecycle: `plan -> start -> implement -> review -> done`. The agent cannot skip stages — quality gates enforce the sequence.

**Quality gates.** Before starting, the agent must define what it's building and how success will be measured (QG-0: Context Gate). Before closing, it must prove each criterion was met with evidence — test output, verification steps (QG-2: Implementation Gate). Tests and linters run automatically.

**Project memory.** Decisions, patterns, conventions, and failed approaches are stored in a local SQLite database with full-text search. When a new session starts, the agent loads this context — no more "who wrote this and why?" from scratch.

**Skills.** Skills are structured prompts that guide the agent through complex workflows. `/plan` breaks down a task, `/review` runs 5 parallel review agents, `/ship` wraps up with review + tests + commit in one step. 33 skills total — from code review to Excel export.

**MCP tools.** 80 tools let the agent interact with the project database programmatically: create tasks, log progress, search memory, manage sessions. MCP (Model Context Protocol) is the standard interface between AI agents and external tools.

**Metrics.** TAUSIK tracks throughput, first-pass success rate, defect escape rate, lead time, dead end rate, and cost per task — automatically, with no manual input.

## Key Features

- **Cross-IDE** — same workflow in Claude Code, Cursor, Windsurf
- **Zero dependencies** — Python 3.11+ stdlib only for core; MCP deps auto-installed in isolated `.tausik/venv/`
- **Quality gates** — agent can't start without a goal, can't close without evidence
- **Project memory** — decisions, patterns, and dead ends persist across sessions (SQLite + FTS5)
- **15 stack-aware checks** — pytest, ruff, tsc, eslint, cargo check, go vet, and more run automatically for your stack
- **6 automatic metrics** — throughput, first-pass success rate, defect rate, lead time — no manual tracking
- **33 skills** — `/plan`, `/ship`, `/review`, `/audit`, `/debug`, and more — structured agent workflows
- **80 MCP tools** — full programmatic access to the project database for the agent
- **Batch execution** — run multi-task plans autonomously with `/run plan.md`

## Supported IDEs

| IDE | MCP Tools | Skills | Hooks (real-time enforcement) | Rules |
|-----|-----------|--------|-------------------------------|-------|
| Claude Code | 80 tools | 33 skills | task gate, bash firewall, push gate, auto-format | CLAUDE.md |
| Cursor | 80 tools | 33 skills | — | .cursorrules |
| Windsurf | 80 tools | 33 skills | — | .windsurfrules |
| Codex | — | — | — | AGENTS.md only |

**Hooks** are real-time enforcement scripts: block code without a task, block dangerous shell commands, block direct push to main. Currently Claude Code only. Other IDEs get the same MCP tools and skills — quality gates still run at `task start` and `task done`, but without pre-action blocking. Codex has minimal support (rules file only, no MCP).

## Dogfooding: TAUSIK Built TAUSIK

TAUSIK was developed using itself from early on. Real numbers from the project:

| Metric | Value |
|---|---|
| Tasks completed | 266 |
| Sessions | 15 |
| Throughput | ~18 tasks/session |
| Test count | 918 |
| Dependencies | 0 core (MCP deps in venv) |

Every feature, every refactor, every bug fix went through the same quality gates that ship with the framework.

## Methodology

TAUSIK implements [SENAR](https://senar.tech) ([GitHub](https://github.com/Kibertum/SENAR)) — an open engineering standard for AI-assisted development that defines quality gates, session management, and metrics. If you're curious about the "why" behind TAUSIK's rules — that's SENAR.

**[Read more about SENAR ->](docs/en/senar.md)**

## Documentation

| Document | Description |
|----------|-------------|
| **[Quick Start](docs/en/quickstart.md)** | First setup — 10-15 minutes |
| **[What is SENAR?](docs/en/senar.md)** | The methodology behind TAUSIK — in 5 minutes |
| **[Workflow](docs/en/workflow.md)** | A typical day with TAUSIK |
| **[Skills](docs/en/skills.md)** | 33 structured agent workflows |
| **[Hooks](docs/en/hooks.md)** | Automatic enforcement: blockers, firewall |
| **[CLI Commands](docs/en/cli.md)** | Full terminal command reference |
| **[MCP Tools](docs/en/mcp.md)** | 80 tools for the AI agent |
| **[Architecture](docs/en/architecture.md)** | How the framework works inside |
| **[Agent Onboarding](AGENTS.md)** | Entry point for AI agents |

**[Full documentation index ->](docs/README.md)**

## Next Steps

- **Try it:** [Quick Start in 10-15 minutes](docs/en/quickstart.md)
- **Understand the methodology:** [What is SENAR?](docs/en/senar.md)
- **See a typical workflow:** [A day with TAUSIK](docs/en/workflow.md)
- **Contribute:** [CONTRIBUTING.md](CONTRIBUTING.md)

## License

[Apache License 2.0](LICENSE)
