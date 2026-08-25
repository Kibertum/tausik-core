---
slug: v14c-visual-cost-dashboard
title: "C5: Visual cost dashboard (Plotly mini-server)"
status: done
epic: landscape-2026-h2
story: l26-provable
complexity: null
role: developer
stack: python
tier: light
call_budget: 25
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - CLAUDE.md
  - README.md
  - README.ru.md
  - "docs/_generated/constants.json"
  - "docs/en/receipts.md"
  - "docs/ru/agent-contract.md"
  - "docs/ru/receipts.md"
  - "harness/claude/mcp/project/handlers.py"
  - "harness/claude/mcp/project/tools.py"
  - "scripts/project_cli_task.py"
  - "scripts/project_cli_verify.py"
  - "scripts/project_parser_task.py"
  - "scripts/service_gates.py"
  - "scripts/service_task.py"
  - "scripts/service_task_done.py"
  - "tests/conftest.py"
  - "tests/test_cli_verify_guards.py"
  - "tests/test_tausik_service.py"
  - "scripts/gate_changelog.py"
  - "tests/test_changelog_gate.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-22T19:09:41Z"
---

## Goal

tausik dashboard — Plotly/Dash локальный server (port 8089) с графиками: tokens by task, cost by session, dead-end rate over time, throughput. Альтернатива текстовому tausik metrics --cost.

## Acceptance Criteria

AC1. Принято и зафиксировано через tausik decide решение: реализовать как opt-in extras (pip install) ЛИБО закрыть задачу как противоречащую stdlib-принципу проекта (прецедент dead-end #27, отказ от ChromaDB).
AC2. Если реализуется: tausik dashboard поднимает локальный сервер (порт 8089) с графиками tokens by task / cost by session / dead-end rate over time / throughput; зависимость Plotly/Dash изолирована в опциональных extras — тест, что базовая установка без extras импортируется и работает.
AC3. Если закрывается: зафиксировано, что уже работающая текстовая tausik metrics --cost покрывает потребность.
CHANGELOG.md [Unreleased] и зеркало CHANGELOG.ru.md обновлены прозаической записью об этом изменении.

## Plan

## Rollback

## Journal

- 2026-07-20T10:40:43Z [planning] — КАНДИДАТ НА ЗАКРЫТИЕ (решение #153, сессия #120). Отложена из 1.5 и не взята за ТРИ релиза. Plotly-дашборд как альтернатива уже работающей tausik metrics --cost, плюс тянет тяжёлую внешнюю зависимость в проект, чей стек заявлен как Python stdlib. Противоречит собственному принципу проекта.
- 2026-07-22T19:09:39Z [implementation] — AC1 ✓ решение зафиксировано через tausik decide #164: закрыть как won't-do (не реализовывать Plotly/Dash). AC3 ✓ зафиксировано, что работающая текстовая tausik metrics --cost покрывает потребность в наблюдаемости стоимости; путь opt-in extras также отклонён с обоснованием. AC2 неприменим (задача закрывается, не реализуется). CHANGELOG.md + CHANGELOG.ru.md обновлены прозой (won't-do запись со ссылкой на dead-end #27 / stdlib-принцип).
