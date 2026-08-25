---
slug: split-oversize-scripts
title: "Сплит oversize файлов: backend, service, cli"
status: done
epic: final-polish
story: final-cleanup
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/project_backend.py, scripts/project_service.py, scripts/project_cli.py, scripts/backend_migrations.py, scripts/service_task.py"
scope_exclude: null
relevant_files:
  - "scripts/project_backend.py"
  - "scripts/project_service.py"
  - "scripts/project_cli.py"
  - "scripts/backend_migrations.py"
  - "scripts/service_task.py"
  - "scripts/service_skills.py"
  - "scripts/backend_crud.py"
  - "scripts/project_cli_ops.py"
  - "scripts/backend_migrations_legacy.py"
  - "scripts/service_cascade.py"
  - "scripts/project_cli_extra.py"
  - "scripts/project.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-08T15:17:17Z"
---

## Goal

Разбить project_backend.py (591), project_service.py (545), project_cli.py (478) на модули ≤400 строк без нарушения архитектуры CLI→Service→Backend

## Acceptance Criteria

1. project_backend.py ≤400 строк (выделить часть в отдельный модуль)
2. project_service.py ≤400 строк (выделить часть в отдельный модуль)
3. project_cli.py ≤400 строк (выделить часть в отдельный модуль)
4. backend_migrations.py ≤400 строк (выделить часть в отдельный модуль)
5. service_task.py ≤400 строк (выделить часть в отдельный модуль)
6. Все импорты работают, pytest проходит без ошибок
7. Архитектура CLI→Service→Backend сохранена
8. Ошибка ImportError не возникает при circular imports между новыми модулями

## Plan

## Rollback

## Journal

- 2026-04-08T15:00:31Z [implementation] — Analysis complete. Split plan: 1) backend: extract session+knowledge CRUD into backend_crud.py, 2) service: extract skill methods into service_skills.py, 3) cli: move some cmd_* to cli_extra, 4) migrations: split old v2-v9 into separate file, 5) service_task: extract cascades into small helper
- 2026-04-08T15:13:42Z [implementation] — Split complete. All 5 oversize files now ≤400 lines. New modules: service_skills.py (219), backend_crud.py (233), project_cli_ops.py (145), backend_migrations_legacy.py (280), service_cascade.py (45). 918 tests pass.
- 2026-04-08T15:13:52Z [implementation] — AC verified: 1. project_backend.py 397 ✓ 2. project_service.py 340 ✓ 3. project_cli.py 346 ✓ 4. backend_migrations.py 158 ✓ 5. service_task.py 375 ✓ 6. All imports work, 918 tests pass ✓ 7. Architecture CLI→Service→Backend preserved via mixins ✓ 8. No circular imports — tested with pytest ✓
