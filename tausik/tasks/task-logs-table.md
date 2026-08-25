---
slug: task-logs-table
title: "Таблица task_logs в БД + структурированное журналирование"
status: done
epic: ralphex-inspired
story: auto-progress
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/backend_schema.py, scripts/backend_migrations.py, scripts/backend_queries.py, scripts/service_task.py, scripts/project_cli.py, MCP handlers"
scope_exclude: null
relevant_files:
  - "scripts/backend_schema.py"
  - "scripts/backend_migrations.py"
  - "scripts/project_backend.py"
  - "scripts/service_task.py"
  - "scripts/project_cli.py"
  - "scripts/project_parser.py"
  - "agents/claude/mcp/project/tools.py"
  - "agents/claude/mcp/project/handlers.py"
  - "agents/cursor/mcp/project/tools.py"
  - "agents/cursor/mcp/project/handlers.py"
  - "tests/test_frai_backend.py"
  - "tests/test_migrations.py"
  - "tests/test_mcp_integration.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-03-29T17:31:43Z"
---

## Goal

task log пишет в отдельную таблицу task_logs с timestamps и phase. Поддержка query, FTS5, MCP tool для чтения. Backward compat с notes.

## Acceptance Criteria

1. Таблица task_logs (id, task_slug FK, message, phase, diff_stats, created_at) в schema v14. 2. task log CLI/MCP пишет в task_logs + notes (backward compat). 3. Новый MCP tool frai_task_logs(slug, phase?) для чтения логов. 4. FTS5 индекс на task_logs.message. 5. Миграция v14 проходит на существующей БД без потери данных. 6. Тесты покрывают CRUD + миграцию. 7. Negative: task_logs для несуществующего slug возвращает пустой список, не ошибку.

## Plan

[{"step": "\u0414\u043e\u0431\u0430\u0432\u0438\u0442\u044c \u0442\u0430\u0431\u043b\u0438\u0446\u0443 task_logs \u0432 backend_schema.py (SCHEMA_VERSION=14)", "done": true}, {"step": "\u041d\u0430\u043f\u0438\u0441\u0430\u0442\u044c \u043c\u0438\u0433\u0440\u0430\u0446\u0438\u044e v14 \u0432 backend_migrations.py", "done": true}, {"step": "\u0414\u043e\u0431\u0430\u0432\u0438\u0442\u044c CRUD queries \u0432 backend_queries.py", "done": true}, {"step": "\u041e\u0431\u043d\u043e\u0432\u0438\u0442\u044c task_log \u0432 service_task.py \u2014 dual write (notes + task_logs)", "done": true}, {"step": "\u0414\u043e\u0431\u0430\u0432\u0438\u0442\u044c CLI \u043a\u043e\u043c\u0430\u043d\u0434\u0443 task logs <slug> \u0434\u043b\u044f \u0447\u0442\u0435\u043d\u0438\u044f", "done": true}, {"step": "\u0414\u043e\u0431\u0430\u0432\u0438\u0442\u044c MCP tool frai_task_logs \u0432 handlers.py + tools.py", "done": true}, {"step": "\u0414\u043e\u0431\u0430\u0432\u0438\u0442\u044c FTS5 \u0442\u0440\u0438\u0433\u0433\u0435\u0440\u044b \u0434\u043b\u044f task_logs.message", "done": true}, {"step": "\u041d\u0430\u043f\u0438\u0441\u0430\u0442\u044c \u0442\u0435\u0441\u0442\u044b: CRUD, \u043c\u0438\u0433\u0440\u0430\u0446\u0438\u044f, FTS5 \u043f\u043e\u0438\u0441\u043a", "done": true}]

## Rollback

## Journal
