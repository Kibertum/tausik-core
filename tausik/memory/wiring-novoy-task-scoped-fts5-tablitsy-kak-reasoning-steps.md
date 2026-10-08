---
slug: wiring-novoy-task-scoped-fts5-tablitsy-kak-reasoning-steps
title: "Wiring новой task-scoped FTS5-таблицы (как reasoning_steps)"
type: pattern
tags:
  - filesize
  - fts5
  - migration
  - mixin
  - renar
  - schema
task: v16r-reasoning-steps-table
edges: []
---

Полная обвязка (v16r-reasoning-steps): 1) backend_schema.py — bump SCHEMA_VERSION + таблица + fts5(content=...,content_rowid=id) + триггеры _ai/_ad (append-only, БЕЗ _au) + индексы. 2) backend_migrations.py — аддитивная миграция (тот же DDL); НЕ добавлять в backend_init rebuild-цикл (новая таблица с триггерами наполняется при insert, как fts_task_logs). 3) CRUD — отдельный *Mixin в новом файле (filesize<400), TYPE_CHECKING-стабы _ins/_q, добавить в bases SQLiteBackend (project_backend.py). 4) Service — отдельный *Mixin, стаб _require_task + be:SQLiteBackend, в bases TaskMixin. 5) CLI — parser (project_parser_task.py) + handler (project_cli_task.py) + рендер в _print_task_detail. 6) MCP — handlers.py dispatch + tools.py schema в ОБОИХ harness/claude И harness/cursor (mirror-тесты test_med_findings_fix/test_plan_skill_agent_aware сравнивают harness==.claude → re-bootstrap обязателен). 7) Doc — gen_doc_constants подхватывает +1 MCP tool; обновить cross-refs (README/AGENTS/docs mcp.md/architecture + docs/README.md site-index + senar-compliance-matrix): N project/main/+rag tools. 8) Тест миграции: raw sqlite3 conn.isolation_level=None (autocommit — run_migrations сам делает BEGIN).
