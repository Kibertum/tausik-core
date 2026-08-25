---
slug: v15s-rule6-rollback-plan
title: "[P0] SENAR Rule 6: Rollback Planning — поле + enforcement"
status: done
epic: v15-senar-hardening
story: v15s-rules
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 60
defect_of: null
scope: "scripts/backend_migrations.py, scripts/project_backend.py, scripts/project_parser_task.py, scripts/project_cli_task.py, scripts/gate_qg0_check.py, scripts/service_task_done.py, harness/*/mcp/project/, docs/ru/senar.md, tests/"
scope_exclude: null
relevant_files:
  - "scripts/backend_migrations.py"
  - "scripts/backend_schema.py"
  - "scripts/project_backend.py"
  - "scripts/project_parser_task.py"
  - "scripts/project_cli_task.py"
  - "scripts/gate_qg0_check.py"
  - "scripts/service_task_done.py"
  - "harness/claude/mcp/project/tools.py"
  - "harness/cursor/mcp/project/tools.py"
  - "docs/ru/senar.md"
  - "tests/test_rule6_rollback.py"
  - "tests/test_qg0_dimensions.py"
  - "tests/test_qg2_gates.py"
  - "tests/test_task_start_model_banner.py"
  - README.md
  - README.ru.md
  - "docs/_generated/constants.json"
  - "tests/test_rag_reindex_hang.py"
  - "tests/test_self_correcting_cli.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-12T00:32:50Z"
---

## Goal

Закрыть Rule 6 Rollback Planning (1/5 — NOT IMPLEMENTED, docs/ru/senar.md честно признаёт). Поле rollback_plan у задачи: QG-0 требует для medium/complex; task done проверяет наличие; шаблоны типовых планов (git revert, migration down, feature flag off). AC: миграция схемы; QG-0/QG-2 интеграция; CLI/MCP поддержка; docs; «Правила 4-6 не применяются» убрано из senar.md.

## Acceptance Criteria

1. Миграция v28: tasks.rollback_plan TEXT; task update/add --rollback-plan; task show отображает. 2. QG-0: для medium/complex отсутствие rollback_plan блокирует task start (ServiceError с шаблонами: git revert, migration down, feature flag off); simple — без требования. 3. task done: отсутствие rollback_plan у medium/complex даёт WARNING (не блок — задачи, начатые до фичи, закрываемы). 4. MCP task_update/task_add принимают rollback_plan. 5. docs/ru/senar.md: Rule 6 строка в таблице, сноска про 4-6 скорректирована на 4-5. 6. Тесты QG-0 блока/прохода + ruff/mypy зелёные.

## Plan

## Rollback

git revert коммита; миграция v28 аддитивна (ALTER ADD COLUMN), даунгрейд не требуется — колонка игнорируется старым кодом

## Journal

- 2026-06-12T00:32:37Z [implementation] — Реализовано: миграция v28 (tasks.rollback_plan) + SCHEMA_VERSION 28 + fresh-schema; CLI task add/update --rollback-plan + task show; QG-0 hard-block ТОЛЬКО для явной medium/complex (81 тест упал при дефолте or-medium — сужено: unset complexity = warning); task done = WARNING (pre-v28 задачи закрываемы); MCP tools.py rollback_plan (handler pass-through); senar.md Rule 6 строка + сноска 4-5. Тесты: test_rule6_rollback.py (10), фикстуры 3 старых файлов дополнены rollback_plan. Инцидент: Set-Content повредил кодировку 5 файлов (gotcha #130), восстановлены из git, правки переделаны через Edit/python. Полный suite: 3368 passed -> после фиксов 2 doc-drift тестов зелёный (badge 3498). Module-clash server.py в тестах решён importlib.
- 2026-06-12T00:32:50Z [implementation] — AC: 1. ✓ v28+schema (test_fresh_db_has_column_and_update_persists), CLI add/update/show. 2. ✓ TestQg0RollbackGate (5: блок medium/complex c шаблонами, simple/unset не блокируются). 3. ✓ TestTaskDoneWarns (2). 4. ✓ MCP tools.py rollback_plan, handler pass-through. 5. ✓ senar.md Rule 6 + сноска 4-5. 6. ✓ full suite 3498, ruff/mypy clean.
