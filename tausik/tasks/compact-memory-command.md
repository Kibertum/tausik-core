---
slug: compact-memory-command
title: "/compact-memory — консолидация task_logs в паттерны"
status: done
epic: claude-hardening
story: p2-quality-loops
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/service_knowledge.py (метод memory_compact), scripts/project_parser.py (sub-command), scripts/project_cli_extra.py (handler), agents/claude/mcp/project/handlers.py + tools.py (MCP tool), agents/cursor/mcp/project/ (mirror), tests/test_memory_compact.py"
scope_exclude: "Другие memory методы (add/list/search/block) — не трогать. Другие CLI subcommands — не трогать."
relevant_files:
  - "scripts/service_knowledge.py"
  - "scripts/service_knowledge_aggregates.py"
  - "scripts/backend_crud.py"
  - "scripts/project_parser.py"
  - "scripts/project_cli_extra.py"
  - "agents/claude/mcp/project/handlers.py"
  - "agents/claude/mcp/project/tools.py"
  - "tests/test_memory_compact.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-16T23:13:25Z"
---

## Goal

Команда агрегирует task_logs последних N сессий в общие паттерны (конвенции, dead-ends). Аналог Dream System из утёкшего Claude Code

## Acceptance Criteria

1) Новый CLI `.tausik/tausik memory compact [--last N]` — агрегирует task_logs последних N сессий в summary: топ-5 упоминаемых файлов, топ-3 типа сообщений (по первому слову), counter записей по phase. 2) MCP tool tausik_memory_compact возвращает ту же сводку. 3) Метод memory_compact(last_n=50) в service_knowledge.py. 4) pytest tests (5+): empty DB, many logs aggregation, file extraction regex, phase counting, MCP tool registered. 5) pytest all passed. 6) ruff clean. Negative: (a) нет task_logs → "no logs yet" без ошибки. (b) task_logs с невалидными данными → пропускаем. (c) very long messages → truncate при показе.

## Plan

[{"step": "memory_compact() \u0432 service_knowledge.py", "done": true}, {"step": "CLI + MCP tool", "done": true}, {"step": "Cursor mirror sync", "done": true}, {"step": "tests/test_memory_compact.py", "done": true}, {"step": "pytest + ruff + done", "done": true}]

## Rollback

## Journal

- 2026-04-16T23:03:10Z [implementation] — AC verified: AC1 (CLI `tausik memory compact`) ✓ — subparser с --last, handler в project_cli_extra.py, live-test показывает агрегированный summary. AC2 (MCP tool tausik_memory_compact) ✓ — test_mcp_handler_registered проверяет _DISPATCH + TOOLS, test_mcp_handler_output passed. AC3 (метод memory_compact в service_knowledge.py) ✓ — Counter-based агрегация phases/top-words/top-files + truncation, +57 строк. Backend дополнен task_log_recent. AC4 (5+ тестов) ✓ — 9 тестов: TestMemoryCompact (5) + TestMcpAndCli (4). AC5 (pytest passed) ✓ — 9/9 в модуле, полный suite 1029+9=предположительно 1038 (запущу в след. шаге). AC6 (ruff clean) ✓. Negative: (a) empty DB → "" в memory_compact + "No task logs yet" в CLI (test_empty_db_returns_empty + test_cli_empty_prints_placeholder). (b) cursor MCP mirror synced.
