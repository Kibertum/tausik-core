---
slug: redact-exists-in-cli-and-is-absent-from-mcp
title: "redact есть в CLI и отсутствует в MCP: поверхности разошлись на новой команде"
status: done
epic: release-110-deferred-from-19
story: release110-open-defects
complexity: simple
role: backend
stack: null
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/mcp_cli_only.py"
  - "tests/test_mcp_cli_only.py"
scope_paths:
  - "scripts/mcp_cli_only.py"
  - "tests/*.py"
  - "docs/ru/cli.md"
  - "docs/en/cli.md"
  - "CHANGELOG*.md"
scope_tools: []
depends_on: []
completed_at: "2026-09-23T20:17:48Z"
---

## Goal

ЗАМЕР, сессия #180: команда tausik redact (dry-run, --apply, redact list) построена только в CLI. В MCP её нет — это было НАМЕРЕННО через scope_exclude задачи nothing-can-redact-the-memory-the-framework-publishes, то есть пропуск осознанный, а не забытый. Но правило проекта гласит MCP-first, и потому осознанный пропуск всё равно оставляет расхождение поверхностей — ровно тот класс, который обязана ловить ratchet-for-mcp-cli-surface-parity. Задача заводится, чтобы расхождение было ЗАПИСАНО и закрыто явно, а не жило молча до тех пор, пока ratchet его не найдёт. Вопрос, который задача обязана задать до работы: выносится ли необратимая половина (--apply) в MCP вообще, или в MCP уезжает только сухой прогон и redact list, а необратимое остаётся ручным.

## Acceptance Criteria

1. Решение записано (decide): redact остаётся в CLI целиком; причина — необратимость --apply и храповик поверхности MCP.
2. scripts/mcp_cli_only.py — реестр команд CLI, намеренно отсутствующих в MCP, у каждой причина и ссылка на решение; redact в нём.
3. НЕГАТИВНЫЙ: тест падает, если запись реестра без причины или если команда из реестра появилась в MCP (реестр солгал бы).
4. docs/ru|en/cli.md у redact говорят, что команда только в CLI и почему.

## Plan

## Rollback

git revert коммита; инструменты MCP аддитивны

## Journal

- 2026-09-23T20:17:20Z [implementation] — Сделано: решение #385 (redact остаётся только в CLI, с двумя отвергнутыми вариантами через новый --rejected); scripts/mcp_cli_only.py — реестр CLI-only с причиной и решением; tests/test_mcp_cli_only.py; docs cli en/ru у redact. NO-DEAD-END: красный локальный прогон — моя опечатка в тесте (искал английское 'decision' в русской странице), исправлено.
- 2026-09-23T20:17:21Z [implementation] — AC-1: ✓ решение #385
- 2026-09-23T20:17:21Z [implementation] — AC-2: ✓ tests/test_mcp_cli_only.py::test_every_entry_says_why_and_on_whose_decision
- 2026-09-23T20:17:22Z [implementation] — AC-3: ✓ tests/test_mcp_cli_only.py::test_a_listed_command_is_not_an_mcp_tool
- 2026-09-23T20:17:22Z [implementation] — AC-3: ✓ tests/test_mcp_cli_only.py::test_the_registry_would_catch_a_tool_that_appeared
- 2026-09-23T20:17:22Z [implementation] — AC-4: ✓ tests/test_mcp_cli_only.py::test_the_cli_docs_say_redact_is_cli_only
