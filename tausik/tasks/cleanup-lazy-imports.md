---
slug: cleanup-lazy-imports
title: "Убрать ненужные lazy imports, dead code, unused variables"
status: done
epic: polish
story: arch-fixes
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/service_task.py"
  - "scripts/project_service.py"
  - "scripts/cq_client.py"
  - "scripts/project_cli.py"
  - "tests/test_skills_maturity.py"
  - "agents/cursor/mcp/project/handlers.py"
  - "bootstrap/bootstrap_copy.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-05T16:34:20Z"
---

## Goal

Нет повторных import sys/re/utcnow_iso внутри методов. Нет unused variables (epic в epic_done). Нет unused imports (urlencode в cq_client).

## Acceptance Criteria

1. service_task.py: import sys, import re, from frai_utils import utcnow_iso — на уровне модуля. 2. project_service.py: epic в epic_done без присваивания. 3. cq_client.py: urlencode убран. 4. Ошибка если ruff check scripts/ показывает F811/F401 warnings.

## Plan

[{"step": "service_task.py: \u0432\u044b\u043d\u0435\u0441\u0442\u0438 import sys, re, utcnow_iso \u043d\u0430 \u0443\u0440\u043e\u0432\u0435\u043d\u044c \u043c\u043e\u0434\u0443\u043b\u044f", "done": true}, {"step": "project_service.py: \u0443\u0431\u0440\u0430\u0442\u044c unused epic = \u0432 epic_done", "done": true}, {"step": "cq_client.py: \u0443\u0431\u0440\u0430\u0442\u044c unused urlencode import", "done": true}, {"step": "project_cli.py: \u0443\u0431\u0440\u0430\u0442\u044c redundant import os \u0432 cmd_run", "done": true}, {"step": "ruff check scripts/ \u2014 0 warnings", "done": true}]

## Rollback

## Journal

- 2026-04-05T16:34:11Z [implementation] — AC verified: service_task.py — sys/re/utcnow_iso на уровне модуля ✓ project_service.py — epic unused убран ✓ cq_client.py — urlencode убран ✓ project_cli.py — redundant import os убран ✓ Также: исправлены test_skills_maturity.py для новой agents/ структуры, синхронизирован cursor MCP. 700/700 тестов прошли.
