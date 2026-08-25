---
slug: after-schema-version-bump-re-run-bootstrap-py-before-tausik
title: "After SCHEMA_VERSION bump — re-run bootstrap.py before tausik CLI calls"
type: gotcha
tags:
  - bootstrap
  - migration
  - schema
task: v14b-usage-events-auto-write
edges: []
---

CLI/MCP читают `.claude/scripts/*` (generated copy от bootstrap.py), а не `scripts/*` (source). Если изменил SCHEMA_VERSION или схемные файлы (backend_schema.py, backend_migrations.py) — ОБЯЗАТЕЛЬНО запусти `.tausik/venv/Scripts/python bootstrap/bootstrap.py` перед `.tausik/tausik <cmd>`, иначе CLI крашится с "no such column X" / version mismatch.\n\nReplay tests/прямые SQLiteBackend('.tausik/tausik.db') миграцию ТРИГГЕРЯТ (на open), но CLI продолжает использовать stale .claude/ копию до пересборки.
