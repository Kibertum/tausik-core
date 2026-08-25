---
slug: v14-audit-unused-python
title: "Инвентаризация: vulture/ruff unused (с конфигом исключений)"
status: done
epic: v14-dead-code-audit
story: v14-audit-inventory
complexity: medium
role: null
stack: null
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/audit_unused_python.py"
  - "tests/test_audit_unused_python.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-02T11:17:51Z"
---

## Goal

Отчёт без поломки legacy.

## Acceptance Criteria

1. Конфиг исключений. 2. Отчёт артефакт. 3. Negative: ложные срабатывания на generated/tests документированы.

## Plan

## Rollback

## Journal

- 2026-05-02T11:17:51Z [implementation] — AC verified: 1. ✓ EXEMPT_MODULES + SOURCE_EXCLUDES + private-helper skip = config исключений, tested via tests/test_audit_unused_python.py::TestExclusionHelpers. 2. ✓ markdown report артефакт через scripts/audit_unused_python.py + --json + --check. 3. ✓ Negative: ложные срабатывания на generated/tests документированы в render_markdown «Documented false positives» секции; hooks/private/exempt skipped без auto-delete.
