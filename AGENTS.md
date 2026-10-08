# AGENTS.md — AI Agent Onboarding

**You are an AI agent working on a project that uses TAUSIK.**
This document tells you what TAUSIK is, why it exists, and how to work with it.

## What is TAUSIK?

TAUSIK is a model-agnostic engineering governance framework implementing
[SENAR v1.5 Core](https://senar.tech). It gives each change a task, goal,
acceptance criteria, verification evidence and a recoverable history.

## Your First 60 Seconds

1. Use MCP `tausik_*`; use `.tausik/tausik` only as fallback.
2. Open the session, then load work with `tausik_task_show` in `package` mode
   (CLI: `task show <slug> --package`). Use full output only for targeted detail.
3. Hosts without slash commands execute `harness/skills/<name>/SKILL.md`.

References: [agent quickstart](docs/en/agent-quickstart.md),
[MCP](docs/en/mcp.md), [CLI](docs/en/cli.md), [skills](docs/en/skills.md).

## Host contract

Claude, Codex, Kilo/GLM, Cursor, Qwen and headless agents use the same MCP and
DB. Hooks enforce rules only where the host supports and trusts them; otherwise
the agent calls session/task operations itself. Never write project knowledge to
`~/.claude/`; use `tausik_memory_*`. See
[model providers](docs/en/model-providers.md) for the enforcement matrix.

## The Rules You Must Follow

1. **No code without a task.** Always create a task (`tausik_task_quick` or `/plan`) before writing code.
2. **QG-0: Define before you start.** Every task needs a goal and acceptance criteria before `task start`. No exceptions.
3. **QG-2: Prove before you close.** Log AC verification evidence via `task log`, then `task done --ac-verified`. No shortcuts.
4. **Log your progress.** Use `tausik_task_log` after each significant step.
5. **Document dead ends.** Failed approach? `tausik_dead_end "what" "why"` — so the next session doesn't repeat it.
6. **Session limit: 180 minutes.** Use `/checkpoint` to save progress. Use `/end` to close properly.
7. **Ask before committing.** Never `git commit` or `git push` without user confirmation.
8. **MCP-first.** Prefer MCP tools over CLI bash commands.

## Testing discipline (agents) — HARD RULES

When you touch TAUSIK core (`scripts/`, `scripts/hooks/`, MCP handlers, gates), or write tests in any project that uses TAUSIK:

1. **Add or extend tests that align with files you changed** so scoped `pytest` on `task done` / `verify --task` stays meaningful.
2. Call **`tausik_verify`** before closure.
3. **Do not duplicate tests.** If a new test has the same structure as an existing one and only differs in inputs — **use `@pytest.mark.parametrize`**. Never add 5 tests where one parametrized test covers the same matrix. Run `python scripts/audit_pytest_dedupe.py` to check.
4. **Do not write tests on trivial getters / `assert callable(f)` / `hasattr(obj, 'attr')` / `assert x is not None` without behavior check** — these tests catch zero bugs and inflate suite time. If the only signal is "the import works", remove the test.
5. **Do not write mock-only tests** where 100% of meaningful calls are mocks and no real code path runs. The test must exercise the SUT.
6. **Do not write tests on implementation detail** (exact log strings, private method names, exact SQL syntax). Test behavior, not implementation.
7. **Security-sensitive paths** (hooks, auth, billing, payment) are **not** exempt — gates and verify-cache rules treat them **stricter**, not looser.

Details, anti-patterns, fake-test detector list: **[docs/en/testing-principles.md](docs/en/testing-principles.md)** · [RU](docs/ru/testing-principles.md).

## Work Cycle

Abbreviated spine: session open (`/start` ↔ `harness/skills/start/SKILL.md` + `tausik_session_*`) → plan (`/plan`, `task_quick`) → **`tausik_task_start` (QG-0)** → implement + `tausik_task_log`/`tausik_dead_end` → **`tausik_verify`** → **`tausik_task_done` (QG‑2)** → optional `/ship` → `/end`.

Canonical narrative + branching detail: **[docs/en/workflow.md](docs/en/workflow.md)** — keep that file authoritative; this header only orients newcomers.

## On-demand references

- Full contract: [workflow](docs/en/workflow.md),
  [agent contract](docs/en/agent-contract.md), [known limitations](docs/en/known-limitations.md).
- Core: `scripts/project.py` → service → backend; gates in `scripts/gate_runner.py`;
  MCP in `harness/claude/mcp/project/server.py`; bootstrap in `bootstrap/bootstrap.py`.
- Details: [architecture](docs/en/architecture.md),
  [testing](docs/en/testing-principles.md), [hooks](docs/en/hooks.md).

The CLI never touches the DB directly. Service validates; backend executes.

## Answer shape

- Use user's language.
- SHAPE, omit empty: done → verified by → left → your call.
- PROSE (no ASD-STE100 claim): name actor/action; active voice if natural; one action/sentence; one term/concept; short paragraphs.
- BYTE-EXACT: code, shell commands, tool output, file paths, error messages; FULL: acceptance-criteria evidence, decisions, SPEC/ADAPT, task logs, handoffs.
- EXCEPTIONS: explanation asked; destructive action; 3 failed debug turns → assumption + question; ambiguity → one question; rule deletes answer itself.
- Steps: numbered, one action each, last ≤2 min; ≤5/group unless more needed; tangent last; estimate if useful.
- PRE-SEND: delete announcements, recaps, side branches, empty hedges; first line = next action; last = current state.


<!-- DYNAMIC:START -->
## Current State
Session: none | Branch: v1-11-3 | TAUSIK: 1.11.3
Tasks: 1819/1898 done, 9 obsolete, 0 active, 0 blocked
Full history (grep it for what a compaction dropped): ~\.claude\projects\d--Work-Kibertum-clients-kibertum-tausik-core\2fb2646a-10b7-4fc5-8fb4-be2e70726533.jsonl

### Memory tail
Context (5):
- #925 Хвост памяти: слои и релевантность (v74, 1.11.3)
- #924 Escape-парадокс решён: левое цензурирование + умершее лечение, а не вред verify
- #922 Tier call budgets recalibrated 2026-10-06 against measured percentiles
- #851 1.11 Codex economy: cache is already high; next leverage is rounds and routing
- #812 1.11: distinguish model/speed subscription cost from token double counting
Decisions (5):
- #427 Релиз 1.11.3 опубликован с замеренной, а не обещанной экономикой: verification-цикл закрыт refusal-веткой (savings не за
- #426 selected_tests is removed from cohort identity inputs; identity placeholders 'declared-at-run'/'selection-evidence-of-ru
- #425 Per-test provenance granularity is a declared non-goal of the verification-cohort contract: cohort identity binds conten
- #424 Escape-задача investigate-the-verified-vs-unverified-escape: политику verify оставляем как есть; агрегатную строку by_ve
- #423 Не переномеровывать эпики бэклога заранее: слот релиза освобождается только после того, как релиз фактически вышел (суще
Conventions (5):
- #799 Переименовал тест — ответь на цитаты в том же заходе, иначе регистр покраснеет следующей проверкой
- #792 Потолок без запаса есть запрет: у бюджета контекста должен быть проверяемый остаток, а не только пре
- #778 Список «к сведению» без владельца переоткрывают, а не закрывают: каждая строка обязана назвать причи
- #777 Намеренный пробел объявляется тремя строками: что НЕ гарантировано, почему живём, что держит границу
- #776 Отчёт о прогоне называет и deselected, иначе «11592 passed» скрывает выключенную ленту
Dead ends (3):
- #930 Duplicating the force-retired unblock test in both test_session_capacity.py and test_session_signal_
- #929 Copy the v49 'is registered' test shape verbatim for the v76 migration test (two bare asserts: N in
- #918 Verify #3521/#3522 red
<!-- DYNAMIC:END -->
