---
slug: handoff-of-any-past-session-is-unreadable
title: "Хэндофф любой сессии, кроме последней, не читается ни CLI, ни MCP"
status: done
epic: release-110-deferred-from-19
story: release110-sessions-are-not-gates
complexity: simple
role: backend
stack: null
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/backend_crud.py"
  - "scripts/service_session.py"
  - "scripts/project_cli.py"
  - "scripts/project_parser_session.py"
  - "harness/claude/mcp/project/handlers_session.py"
  - "harness/claude/mcp/project/tools.py"
  - "tests/test_past_handoff_is_readable.py"
  - "docs/ru/cli.md"
  - "docs/en/cli.md"
  - "docs/ru/mcp.md"
  - "docs/en/mcp.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths:
  - "scripts/project_cli*.py"
  - "scripts/project_parser_session.py"
  - "scripts/service_session.py"
  - "scripts/backend_crud.py"
  - "harness/claude/mcp/project/*.py"
  - "tests/*.py"
  - "docs/ru/*.md"
  - "docs/en/*.md"
  - "CHANGELOG*.md"
scope_tools: []
depends_on: []
completed_at: "2026-09-23T17:14:07Z"
---

## Goal

ЗАМЕР, сессия #181: session last-handoff отдаёт ТОЛЬКО свежайший хэндофф; команды session show <id> нет; session list печатает summary, но не handoff; events по entity=session несут только tool_use. Следствие измерено на живом случае: таблица разбора PR #5 была записана в хэндофф сессии #179, инструкция владельца гласила «заново не разбирать», и достать её пришлось ИЗ ТРАНСКРИПТА IDE, то есть из-за пределов фреймворка. Фреймворк, обещающий непрерывность контекста между сессиями, теряет её на глубине один. Правило AC: чтение хэндоффа по номеру сессии обязано быть в CLI и в MCP (MCP-first), и обязано быть закреплено тестом, который краснеет на сегодняшнем дереве.

## Acceptance Criteria

1. session last-handoff --session N (CLI) и tausik_session_last_handoff с session_id (MCP) печатают handoff сессии N; без аргумента поведение прежнее — свежайший.
2. НЕГАТИВНЫЙ: несуществующая сессия N — явный ответ «сессии N нет», а не пустота и не чужой handoff; сессия без handoff — «у сессии N handoff не записан».
3. session list печатает столбец, по которому видно, у каких сессий есть handoff.
4. Тест на CLI-разбор и на сервис; docs/ru+en cli.md и mcp.md; CHANGELOG EN+RU.

## Plan

## Rollback

git revert коммита; команда аддитивна, существующий last-handoff не меняется

## Journal

- 2026-09-23T17:13:59Z [implementation] — AC verified: 1 — session last-handoff --session N и tausik_session_last_handoff(session_id) читают handoff сессии N (tests/test_past_handoff_is_readable.py::test_the_handoff_of_an_earlier_session_is_readable, ::test_the_cli_and_the_mcp_tool_take_the_session_number); без аргумента — живой, как прежде. 2 — НЕГАТИВ ::test_a_missing_session_is_named_not_answered_with_another и ::test_a_session_without_a_handoff_says_so (разные отказы). 3 — session list печатает столбец handoff. 4 — docs cli.md и mcp.md ru/en, CHANGELOG EN+RU; поверхность MCP в пределах храповика. Verify #2695 зелёный.
- 2026-09-23T17:14:00Z [implementation] — verify #2695 green; tests/test_past_handoff_is_readable.py 4 tests incl. 2 negatives
