**English** | [Русский](README.ru.md)

# TAUSIK

**AI development framework — plan, build, ship with quality control.**

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB.svg)](https://python.org)
[![Tests](https://github.com/Kibertum/tausik-core/actions/workflows/tests.yml/badge.svg)](https://github.com/Kibertum/tausik-core/actions/workflows/tests.yml)
[![3362 tests](https://img.shields.io/badge/tests-3362%20passed-brightgreen.svg)](#dogfooding-tausik-built-tausik)
[![Zero deps](https://img.shields.io/badge/dependencies-0-brightgreen.svg)](#what-you-get)

> ⚠️ **v1.4 — near-stable pre-2.0 release.** This is the last 1.x minor before
> the major bump to **2.0**. v1.4 ships a very large change set (B+C polish
> phases — verify-first contract, brain artifact pipeline, audit suite, skill
> bundles, two-axis variants, per-task cost/token budgets); expect occasional
> doc-vs-behaviour drift and rough edges on uncommon paths. The core is covered
> by 3362 tests and is dogfooded daily — if you hit a mismatch, file an issue
> and we'll converge it before 2.0.

**TAUSIK is a quality control framework for AI coding agents** — Claude Code,
Cursor, VSCode Claude Extension, Qwen Code, Windsurf. It enforces the
discipline of a senior engineer: plan before coding, verify before claiming
done, remember decisions across sessions, and never silently skip the
test/lint pipeline.

**Think of it as Git for AI workflow.** Sessions, tasks, decisions and
dead-ends are tracked in a local SQLite database. Quality gates physically
block the agent at two checkpoints — start (no goal? blocked) and done
(no evidence? blocked) — so "I'll remember to test next time" stops being a thing.

Three messages. Full engineering cycle. Quality gates that the agent can't skip.

> Works across Claude Code, VSCode Claude Extension, Cursor, Qwen Code (GigaCode), Windsurf.

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

## Token Efficiency

v1.4.x ships fewer skills by default — only the ones every TAUSIK project actually uses. Smaller system-reminder list = lower per-turn token cost without losing functionality.

| Component | Before v1.4.x | After v1.4.x | Saving |
|---|---|---|---|
| `system-reminder` skill list | 38 skills (~1,520 tok/turn) | 12 + 1 conditional (~480 tok/turn) | **−1,040 tok/turn (−68%)** |

How it works:

- **12 core skills** auto-deployed: `/start`, `/end`, `/checkpoint`, `/plan`, `/task`, `/ship`, `/commit`, `/review`, `/test`, `/debug`, `/explore`, `/interview`.
- **`/brain` conditional** — surfaces only when `tausik brain init` has populated `brain.notion_db_ids`. Projects that never use the shared brain don't pay its ~600 tok/turn.
- **Extras opt-in** — re-run `python .tausik-lib/bootstrap/bootstrap.py --include-official` (alias `--include-vendor`) for the full 38-skill set, or `tausik skill install <name>` for one at a time. Bundle CLI (`tausik skill bundle install`) lands in a follow-up release.
- **`tausik status` warns** if the deployed skill set drifts from the active flag (e.g. 38 deployed without `--include-official`) so you notice unintended bloat.

## Functionality

| Category | What it does | How you use it |
|---|---|---|
| **Lifecycle** | Epic → Story → Task hierarchy with state machine (planning → active → review → done) | `/plan`, `/task`, `/start`, `/end` |
| **Quality Gates** | QG-0 blocks `task start` without goal+AC. QG-2 blocks `task done` without verify-cache hit. Scoped per task — only relevant tests run | Auto on `task start` / `task done` |
| **Verify-First Contract** *(v1.4)* | Heavy gates (pytest, tsc, cargo, phpstan…) on a `verify` trigger separate from `task done`. Closing a task is millisecond. Pipeline envelope timeout 60s — no silent hangs | `tausik verify --task X` then `task done X` |
| **Project Memory** | Patterns, gotchas, conventions, dead-ends, decisions stored in SQLite+FTS5. Re-injected at session start | `/brain`, `tausik memory add`, auto on `/start` |
| **Verification Engine** | 25 stack-aware checks (pytest, ruff, mypy, tsc, eslint, cargo, go-vet, phpstan, helm-lint, hadolint…). Scoped to relevant_files. Cached for 10 min | Stack auto-detected by bootstrap |
| **Real-time Hooks** | 19 hooks: task gate (no code without task), bash firewall, push gate, auto-format, drift detection (SessionStart/UserPromptSubmit/Stop), memory pre/post audit | Auto in Claude Code & Qwen Code |
| **Metrics** | Throughput, First-Pass Success Rate, Defect Escape Rate, Lead Time, Dead End Rate, Cost-per-task | `tausik metrics`, `tausik metrics --cost` |
| **Multi-IDE** | Same MCP tools (100) + skills across hosts | VSCode/Claude, Cursor, Qwen Code, Windsurf, Codex, CLI |
| **Skill Ecosystem** | 12 core skills auto-deployed (+ `/brain` when configured) — see [Token Efficiency](#token-efficiency). 25+ official/vendor skills opt-in via `--include-official` flag or `tausik skill install`. Multi-model profiles via `variants/<model>.md` *(v1.4)* | `tausik skill install <name>` |
| **Cross-project Brain** *(optional)* | Notion-mirrored decisions / patterns / gotchas / web-cache shared across projects. v1.4 adds an artifact pipeline: propose → audit (scrubbing for secrets) → publish, with stack-aware bm25 ranking. Privacy via SHA256 project hashes | `/brain` query, `tausik brain init`, `tausik brain propose-artifact`, `tausik brain publish` |
| **Hygiene & Audit** *(v1.4)* | `tausik hygiene archive` lists old done tasks (dry-run). Audit scripts: `audit_orphan_files`, `audit_stale_docs`, `audit_unused_python`, `audit_pytest_dedupe` — inventory dead code, dangling docs, copy-pasted tests | `tausik hygiene archive`, `python scripts/audit_*.py` |
| **Task Archive** *(v1.4)* | Read-only spec for archiving done tasks > N days. Active / blocked / planning never archived; `--confirm` reserved for future destructive ops | `tausik hygiene archive` |
| **Batch Execution** | Run multi-task markdown plans autonomously | `/run plan.md` |
| **Sessions** | Active-time tracking (gap-based, 10-min idle threshold), 180-min limit, capacity gate (200 tool calls), handoff persistence | Auto on `/start`, `/end`, `/checkpoint` |

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

## Advanced Features

- **Anti-drift guards** — SessionStart / UserPromptSubmit / Stop hooks detect coding intent without an active task, re-inject Memory Block on `/start`, audit `task_done` evidence (file paths, ✓ markers, test counts, lint status). Adversarial critic — 6th parallel `/review` agent finds weaknesses the others miss. [Details →](docs/en/hooks.md)
- **Memory discipline** — TAUSIK memory (`.tausik/tausik.db`, project-scoped) and Claude auto-memory (`~/.claude/`, cross-project) are separated by a PreToolUse block + PostToolUse audit. Project leaks into cross-project memory are blocked at the source. [Details →](docs/en/memory-merge-guidelines.md)
- **Shared Brain** *(optional)* — second knowledge layer on Notion for cross-project patterns + gotchas. Local SQLite FTS5 mirror, bm25-ranked search, SHA256-hashed project names. Stdlib-only Notion client. [Details →](docs/en/shared-brain.md)
- **Brain artifact pipeline** *(v1.4)* — formal taxonomy (artifact / pattern / snippet) + JSON Schema validator + propose→audit→publish flow with scrubbing for secrets and explicit `confirm_high_risk` gate. Stack-aware ranking in `brain_search`. [Taxonomy →](docs/en/brain-artifact-taxonomy.md) · [Search ranking →](docs/en/brain-search-ranking.md)
- **Pipeline reliability** *(v1.4)* — Verify-First contract decouples heavy gates from `task done`. Envelope timeout (60s default), relaxed cache for manual-scope verify, relevant_files fallback from verify-row. No silent hangs. [Details →](docs/en/verify-glossary.md)
- **Audit suite** *(v1.4)* — orphan-file / stale-doc / unused-python / pytest-dedupe scripts surface dead code and copy-paste in long-running projects. `tausik hygiene archive` + read-only task archive spec. CI doc-constants drift check. [Details →](docs/en/dev-doc-checks.md)
- **Interview & live dashboard** — `/interview` runs Socratic Q&A before complex tasks. `tausik hud` shows one-screen live dashboard. `tausik suggest-model` routes Haiku/Sonnet/Opus by task complexity. Webhook notifications to Slack/Discord/Telegram.

## What's Inside

- **12 core skills + `/brain` conditional** (auto-deployed) — `/start`, `/end`, `/checkpoint`, `/plan`, `/task`, `/ship`, `/commit`, `/review`, `/test`, `/debug`, `/explore`, `/interview` always; `/brain` only after `tausik brain init`. Plus **25+ official/vendor skills** (`/audit`, `/zero-defect`, `/markitdown`, `/docs`, `/security`, `/onboard`, …) opt-in via `bootstrap --include-official` or `tausik skill install <name>`.
- **103 MCP tools** (96 project + 7 brain) — full programmatic access to the project database
- **25 quality checks** — pytest, ruff, tsc, eslint, cargo check, go vet, and more for your stack
- **6 automatic metrics** — throughput, first-pass success rate, defect rate, lead time
- **Project memory** — SQLite + FTS5, graph relations, dead-end tracking, Memory Block re-injection
- **19 Claude Code hooks** — task gate, bash firewall, push gate, auto-format, activity event, SessionStart, UserPromptSubmit, Stop × 2, PostToolUse verify, memory pre-write block, memory post-write audit, brain post-WebFetch cache, brain pre-search proactive, notify-on-done, session-metrics, session-cleanup-check, task-call-counter
- **Batch execution** — `/run plan.md` executes multi-task plans autonomously
- **Zero dependencies** — Python 3.11+ stdlib only; MCP deps in isolated `.tausik/venv/`

## Supported IDEs

**Validation policy:** TAUSIK is designed to be multi-IDE, but release validation is explicit.
Officially tested E2E right now: **VSCode + Claude Extension** and **Cursor**.
Other integrations are supported by design, but are marked as expected/partial until full test matrix coverage is added.

| IDE | MCP Tools | Skills | Hooks | Rules | Validation status |
|-----|-----------|--------|-------|-------|-------------------|
| VSCode + Claude Extension | 103 tools | 12 core + brain conditional, 25+ on demand | 19 hooks (task gate, bash firewall, push gate, auto-format, activity, memory guards, brain auto-cache, ...) | CLAUDE.md + .mcp.json | **Officially tested** |
| Cursor | 103 tools | 12 core + brain conditional, 25+ on demand | — | .cursorrules + .cursor/mcp.json | **Officially tested** |
| Claude Code (CLI) | 103 tools | 12 core + brain conditional, 25+ on demand | 19 hooks | CLAUDE.md + .mcp.json | Expected (partial matrix) |
| Qwen Code | 103 tools | 12 core + brain conditional, 25+ on demand | 19 hooks (same as Claude) | QWEN.md + .mcp.json | Expected (partial matrix) |
| Windsurf | 103 tools | 12 core + brain conditional, 25+ on demand | — | .windsurfrules + .mcp.json | Expected (partial matrix) |
| Codex / OpenCode-style agents | MCP + rules-driven where supported | Depends on host | Host-specific | AGENTS.md | Expected (manual validation) |

**Hooks** block code edits without a task, dangerous shell commands, and direct push to main — in real time. Available in Claude Code and Qwen Code. Cursor and Windsurf get the same MCP tools and skills, with quality gates at `task start` and `task done`.

## Dogfooding: TAUSIK Built TAUSIK

TAUSIK was developed using itself. Real numbers:

| Metric | Value |
|---|---|
| Tasks completed | 526 |
| Sessions | 39 |
| Throughput | ~13 tasks/session |
| Test count | 2590 |
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
| **[Skills](docs/en/skills.md)** | 12 core + brain conditional, 25+ official skills opt-in (38 total) |
| **[Hooks](docs/en/hooks.md)** | Real-time enforcement |
| **[CLI Commands](docs/en/cli.md)** | Terminal command reference |
| **[MCP Tools](docs/en/mcp.md)** | 103 tools for the AI agent |
| **[Architecture](docs/en/architecture.md)** | How the framework works inside |

**[Full documentation ->](docs/README.md)**

## License

[Apache License 2.0](LICENSE)
