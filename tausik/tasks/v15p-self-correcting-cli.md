---
slug: v15p-self-correcting-cli
title: "[P0] T1: Самокорректирующийся CLI — usage-блок в ошибках аргументов"
status: done
epic: v15-polish
story: v15p-agent-ux
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 60
defect_of: null
scope: "scripts/project_parser*.py, scripts/project_cli.py, harness/*/mcp/project/, tests/"
scope_exclude: null
relevant_files:
  - "scripts/project_parser_errors.py"
  - "scripts/project_parser.py"
  - "harness/claude/mcp/project/server.py"
  - "harness/cursor/mcp/project/server.py"
  - "tests/test_self_correcting_cli.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-11T23:52:08Z"
---

## Goal

Лечим «агент гадает аргументы» (источник: docs-mcp-server grounding-паттерн, отчёт docs/research/2026-06-12 T1). При ошибке парсинга аргументов CLI и MCP возвращать машиночитаемый usage-блок: синтаксис подкоманды + 1-2 примера вызова, чтобы агент восстанавливался за одну итерацию. AC: argparse error handler переопределён глобально; MCP InputValidation ошибки включают usage; e2e-тест «неверный вызов → в ответе есть корректный пример»; покрыты топ-10 команд по частоте ошибок из usage_events.

## Acceptance Criteria

1. argparse error handler переопределён глобально: ошибка аргументов → exit 2 + usage подкоманды + 1-2 примера. 2. MCP-ошибки валидации входа включают usage/пример. 3. E2e-тест: неверный вызов → ответ содержит корректный пример. 4. Примеры покрывают топ-10 команд по ошибкам из usage_events (или все основные при недостатке данных).

## Plan

## Rollback

## Journal

- 2026-06-11T23:51:58Z [implementation] — SelfCorrectingParser (project_parser_errors.py): error() = message + usage + longest-prefix examples (15 команд) + hint; subparsers наследуют класс от root. MCP: server._usage_hint генерирует usage из inputSchema при любой ошибке handler'а. 12 новых тестов + e2e через wrapper подтверждён.
- 2026-06-11T23:52:08Z [implementation] — AC: 1. ✓ tests/test_self_correcting_cli.py::TestCliErrors (5) + e2e wrapper exit2+example. 2. ✓ TestMcpUsageHint (3). 3. ✓ test_cli_e2e_subprocess_error_contains_example. 4. ✓ EXAMPLES: 15 основных команд (usage_events анализ отложен — недостаток данных об ошибках в БД).
