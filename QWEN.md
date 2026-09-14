# QWEN.md

You are Qwen Code (an AI coding agent) working on this project. Follow these instructions strictly.

## Project: my-project

Stack: python
Framework: [TAUSIK](https://github.com/Kibertum/tausik-core) — AI agent governance implementing [SENAR v1.3](https://senar.tech)

Quality gates enforce these automatically: bootstrap deployed 32 hook commands into this host's profile, so a violation is refused rather than reported.

## Hard Constraints (non-negotiable)

- **No code without a task.** Run `task start <slug>` before any Write/Edit. No exceptions. (SENAR Rule 9.1)
- **QG-0 Context Gate.** `task start` requires goal + acceptance_criteria; work that changes behaviour names at least one negative scenario, work that changes only prose does not. Set both before starting.
- **QG-2 Implementation Gate (Verify-First v1.4).** Heavy gates (pytest, tsc, cargo, phpstan, …) live on a separate `verify` step. Sequence: run `tausik verify --task <slug>` once everything is in place — it caches a green; then `task done --ac-verified` looks the cache up and closes the task in milliseconds. If the cache is missing or stale → `task done` blocks with the explicit remediation command. Opt-out for CI: `.tausik/config.json` → `{ "task_done": { "auto_verify": true } }` (legacy inline behavior).
- **No commit without gates, and verification is PROPORTIONATE to the change.** Gates run automatically — fix blocking failures before committing. Run the scoped `verify` for what you touched; the full suite belongs in CI and at the release gate, not after every local step. A test asserts behaviour — never a number in a document, never that a generated file is fresh (whatever moves its source regenerates it). One test that goes red on the defect beats a suite that goes red on bookkeeping.
- **No direct DB access.** Use MCP tools or CLI. Never raw SQLite.
- **Don't guess CLI arguments.** Run `.tausik/tausik <cmd> --help` or read the CLI reference.
- **MCP-first.** Prefer MCP tools (`tausik_*`) over CLI when equivalent.
- **Git: ask before commit/push.** Always request user confirmation.
- **Max 500 lines per file.** Filesize gate warns. Exceptions: tests, generated code.
- **Continuous logging.** Run `task log <slug> "message"` after every meaningful step. (SENAR Rule 9.4)
- **Document dead ends.** Run `.tausik/tausik dead-end "approach" "reason"` on failed approaches. (SENAR Rule 9.4)
- **Checkpoint every 30-50 tool calls.** Save context periodically. (SENAR Rule 9.3)
- **Session limit: 180 min.** `.tausik/tausik status` warns on overrun. Close the session before starting a new one. (SENAR Rule 9.2)

## Workflow

```
start → plan → task → [review | test] → commit → end
```

- `start` — load session state, active tasks, handoff from previous session · `plan` — create task with complexity scoring + stack detection
- `task <slug>` — pick up or continue a task · `review` — code review with parallel sub-agents (bugs, fake tests, drift)
- `test` — run or write tests · `commit` — standardized commit with SENAR metadata · `end` — close session with handoff for next agent

**Cost-aware model selection:** `tausik suggest-model <complexity>` prints a recommended Claude model (Haiku for simple 1 SP tasks, Sonnet for medium 3 SP, Opus for complex 8 SP). Claude Code doesn't switch models programmatically — apply the suggestion manually via the IDE model picker, and persist your default for the next session with `tausik config set model_profile <slug>` (note: `/fast` only toggles fast-output on Opus, it does NOT downgrade to a smaller model).

## Tool Routing — when to use which

Don't reach for `Grep`/`Glob` first. TAUSIK ships dedicated retrieval MCP servers; using them keeps context lean and surfaces project-specific knowledge that raw text search cannot.

| Need | Primary | Fallback |
|---|---|---|
| Find a function/symbol/usage in code | `mcp__codebase-rag__search_code` | `Grep` (only if RAG returns no hits or index is stale) |
| Recall a past project decision | `tausik_decisions_list` / `tausik_memory_search` (`type=convention/pattern`) | — |
| Cross-project pattern or gotcha | `tausik_memory_search` (the shared store is folded into the results) | — |
| Web lookup (docs, API, errors) | `WebFetch` | — |
| Understand the project structure | `tausik_status` + `tausik_roadmap` | `Glob` for raw file listing |

Run `mcp__codebase-rag__rag_status` once per session to confirm the index is fresh. If `chunks=0`, run `mcp__codebase-rag__reindex` before any `search_code` call.

## Memory (choose the destination by what the fact is about, not by where you are)

| Destination | Where | What goes there |
|---|---|---|
| **Project memory** (`memory add`) | `.tausik/tausik.db` | "Here it is done this way": patterns, dead ends, conventions, environment facts of THIS project. Types: `pattern`, `gotcha`, `convention`, `context`, `dead_end` |
| **Shared knowledge** (`memory add --global`) | `~/.tausik-knowledge/knowledge.db`, read back in every project as *Shared knowledge — from other projects* | "The tool is built this way": a gotcha of a library, a platform habit, a fact true outside this repository. Not redacted — never a secret or a client name |
| **Agent auto-memory** | host-specific (e.g. `~/.claude/...`) | "This is how I like to work": the user's own preferences and cross-project habits — never a fact about a project |

**Memory-first recall (hard rule).** Before asking the user for — or guessing — an established
project fact (hosts, environments, where credentials live, paths, service URLs, prior decisions),
you MUST `memory_search` / `decisions_list` FIRST; asking for something already recorded is a
process violation. Record durable environment facts as `context` so future sessions inherit them.

**Routing litmus (hard).** *Would another agent, in another tool, need this to work on THIS
project?* → `memory add`. *Is it true beyond this project — of the tool, the platform, the library?*
→ `memory add --global`. Never your host's own memory (`~/.claude/**/memory/`, `.cursor/rules/`,
`.windsurf/rules/`, `.github/copilot-instructions.md`, `.github/instructions/`, `.clinerules`, `.roo/rules/`,
`.continue/rules/`, `.aider*` — blocked by the `memory_route` gate); a cloud-side memory writes no
file for any gate to see, so there this line is the only enforcement. Skills that need persistent
data respect `CLAUDE_PLUGIN_DATA` when set, else `.tausik/plugin_data/`.

## Compaction contract (what must survive a context compaction)

Compaction can be instructed; an uninstructed one drops the context whose value shows up later. When your host compacts the conversation, carry these forward VERBATIM, by name — and drop narration, tool output and resolved intermediate states first:
1. **The active task and its slug** — and its current plan step.
2. **The declared scope and the verify receipt** — `relevant_files`, the last `verify` run id / handle.
3. **This session's measurements with their numbers** — a lost measurement costs the run that produced it.
4. **Retired or superseded rules** — a forgotten retirement resurrects a dead rule.
5. **Owner prohibitions** — in the owner's words.
6. **Open forks** — decisions raised and not taken, with the options named.

## SENAR Rules Compliance

TAUSIK enforces these rules. Violating them triggers warnings or hard blocks.

| Rule | Purpose | Enforcement |
|---|---|---|
| QG-0 Context Gate | Goal + AC + negative scenario before starting | Hard (CLI/MCP — blocks `task_start`) |
| QG-2 Implementation Gate | Evidence + AC verified + fresh `tausik verify` green before done (Verify-First v1.4) | Hard (CLI/MCP — blocks `task_done`) |
| Rule 1 Task before code | No Write/Edit without active task | Hard where a real-time mechanism is deployed — the notice at the top of this file says whether that is the case here |
| Rule 2 Scope Boundaries | Declare scope + scope_exclude per task | Warning |
| Rule 3 Verify Against Criteria | Per-criterion evidence | Warning |
| Rule 7 Root Cause | Defect tasks require root cause | Warning |
| Rule 9.2 Session limit | 180 min per session | Hard (blocks `task_start`) |
| Rule 9.3 Checkpoint | Every 30-50 tool calls | Instruction |
| Rule 9.4 Dead Ends + Logging | Document failed approaches, log progress | Instruction |

> **Where "Hard" is hard.** Rule 1 is a process gate only on a host where TAUSIK deployed a real-time mechanism; the notice at the top of this file states which case this host is in, derived from what bootstrap actually wrote. Where it is not deployed, Rule 1 is enforced by the agent reading this line — because TAUSIK generates no payload for that host, NOT because the host cannot accept one; only the first claim is ours to make. The rest hold everywhere: QG-0, QG-2 and the session limit live in the `tausik-project` MCP server and the CLI. For a process-level Rule 1 without a mechanism, route writes through `tausik_task_start` / `tausik_task_done_v2` and treat raw file edits as non-conformant in review.

Full rule set: [SENAR v1.3](https://senar.tech).

## Commands Quick Reference

Seven carry the workflow; 53 commands exist — `.tausik/tausik --help` lists them.

```bash
.tausik/tausik status                          # project overview + warnings
.tausik/tausik task start <slug>               # activate (QG-0 enforced)
.tausik/tausik verify --task <slug> && .tausik/tausik task done <slug> --ac-verified  # QG-2
.tausik/tausik task log <slug> "message"       # log progress
.tausik/tausik dead-end "approach" "reason"    # document failure (used 0 times in 5,966 calls)
.tausik/tausik symbol <name>                   # a definition, its file:line and callers
.tausik/tausik graph show <path>               # what this file changes with, and on what evidence
```

## Quality Gates

Gates run on three triggers:

- **`task-done`** — cheap-only (filesize, tdd_order). Closes a task in milliseconds.
- **`verify`** — heavy (pytest, tsc, cargo, phpstan, javac, js-test, terraform-validate, helm-lint, kubeval, hadolint, ansible-lint). Run via `.tausik/tausik verify --task <slug>`. Result cached for 10 min; `task done` reads the cache.
- **`commit`** — local lint (ruff, eslint, phpcs, golangci-lint).

Stack-specific gates auto-enable by detected stack. Filesize gate warns on files >500 lines.

Check status: `.tausik/tausik gates status`. Fix blocking failures before committing. Verify-First Contract opt-out: `.tausik/config.json` → `{ "task_done": { "auto_verify": true } }` runs the heavy gates inside `task done` instead of as a separate step.

## Skills

After bootstrap, **13 core skills** ship from `harness/skills/` and are always available: `/start`, `/end`, `/checkpoint`, `/plan`, `/task`, `/ship`, `/commit`, `/review`, `/test`, `/debug`, `/explore`, `/interview`, `/reason`, `/i-have-adhd`.

**25+ official/vendor skills** are opt-in via `python .tausik-lib/bootstrap/bootstrap.py --include-official` (full bundle) or `tausik skill install <name>` (per skill) from the `tausik-skills` repo or `skills-official/`: `/audit`, `/zero-defect`, `/markitdown`, `/excel`, `/pdf`, `/docs`, `/security`, `/onboard`, `/retro`, `/ultra`, `/jira`, `/bitrix24`, `/sentry`, ... See `.qwen/references/skill-catalog.md`.

**Security — external skill repos are arbitrary code + instructions.** Adding a repo clones remote content; installing may run pip/scripts. Only use `tausik skill repo add <url>` for trusted sources; third-party URLs require `--force` after review. See `docs/en/vendor-skills.md` and `docs/en/skill-ecosystem.md`.

When a user request matches a trigger keyword for a not-installed skill, proactively suggest installing it.

## Roles

Role field is free text. Common: `developer`, `architect`, `qa`, `tech-writer`, `ui-ux`.
Role profiles live in `.qwen/roles/<role>.md`.

## Are you a non-Claude agent? (GPT-5.5, Composer, Codex, OpenCode, Gemini …)

TAUSIK is model-agnostic, but the surface you actually use differs from Claude Code:

- **MCP tools first.** Every quality gate (QG-0, QG-2, session limit, dead-end tracking) is enforced inside the `tausik-project` MCP server. Calling MCP tools gives you the same hard guarantees Claude Code gets. Bash CLI is a fallback only when MCP is unreachable.
- **Slash commands may not exist.** If your host doesn't expand `/start`, `/plan`, `/ship`, `/end`, open the matching `harness/skills/<name>/SKILL.md` and execute its numbered steps. Skills are written as procedures, not host-specific magic.
- **PreToolUse hooks may not be deployed here.** The notice at the top of this file says whether they are, counted from this host's profile. Where they are not, `task_gate.py` does not protect Rule 1 ("no code without a task") and you self-enforce: always call `tausik_task_start` (or `tausik_task_quick`) before any Edit/Write. The reason is that TAUSIK generates no hooks payload for some hosts — what a given host is capable of accepting is a separate question, and not one this file answers.
- **Don't write to `~/.claude/`.** It is a Claude-specific profile. Use the project DB (`.tausik/tausik.db`) via `tausik_memory_*` MCP tools, or the path under `CLAUDE_PLUGIN_DATA` if your host sets it.
- **Verify-First Contract is universal.** Run `tausik_verify` before `tausik_task_done_v2`, regardless of model. The 60s per-MCP-tool timeout that VS Code Claude Extension applies is the strictest case; if you keep heavy work inside `verify`, every other host stays in budget too.
- **`task_done_v2` over `task_done`.** When the MCP server publishes both, prefer `tausik_task_done_v2` — its structured JSON response (`stage`, `gate_results`, `blocking_failures`) is much friendlier to non-Claude tool-use loops that expect typed payloads.

## Response Language

Always respond in the user's language.


## IDE-specific overrides (qwen)

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

<!-- DYNAMIC:START -->
<!-- DYNAMIC:END -->
