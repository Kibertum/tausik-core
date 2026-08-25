---
slug: v15-scope-declare
title: "[P0] Задача декларирует разрешённые пути/инструменты (scope)"
status: done
epic: v15-evidence-attestation
story: v15-scope-acl
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/scope_acl.py"
  - "scripts/service_task.py"
  - "scripts/project_cli_task.py"
  - "scripts/project_parser_task.py"
  - "scripts/project_backend.py"
  - "scripts/backend_schema.py"
  - "scripts/backend_migrations.py"
  - "tests/test_scope_acl.py"
scope_paths:
  - "scripts/scope_acl.py"
  - "scripts/backend_*.py"
  - "scripts/project_*task*.py"
  - "scripts/service_task.py"
  - "tests/test_scope_acl.py"
scope_tools:
  - Edit
  - Write
depends_on: []
completed_at: "2026-06-12T01:05:19Z"
---

## Goal

Добавить задаче поле scope (allowed paths/globs + опц. tools) — схема БД + аргументы task_add/task_update. Основа для ACL-энфорсмента (SENAR Rule 2).

## Acceptance Criteria

1. Миграция v30: tasks.scope_paths + tasks.scope_tools (JSON-списки), base DDL синхронизирован. 2. task add/update CLI принимают --scope-paths/--scope-tools (nargs), хранится канонический JSON; task show отображает. 3. Негативный: пустые строки/не-список -> ServiceError с пояснением, задача не обновлена. 4. scope_acl.parse_task_acl(task) -> {paths,tools}; негативный: битый JSON в БД -> пустой ACL + warning в лог, БЕЗ исключения. 5. pytest: normalize/parse/CRUD/негативы.

## Plan

## Rollback

git revert: колонки scope_paths/scope_tools аддитивны, NULL = нет ACL (текущее поведение), enforcement ещё не включён — откат не ломает данные, миграция вниз не нужна

## Journal

- 2026-06-12T01:05:18Z [implementation] — AC verified: 1. OK migration v30 + base DDL, live DB migrated. 2. OK CLI dogfood --scope-paths/--scope-tools canonical JSON + task show; TestServiceCrud. 3. OK TestServiceCrud::test_invalid_input_raises_service_error_and_keeps_row + TestNormalize rejects. 4. OK TestParse corrupt/non-list JSON degrades to empty, no exception. 5. OK pytest tests/test_scope_acl.py 17 passed; -k task/backend/scope 429 passed.
