---
slug: v14-audit-orphan-files
title: "Отчёт orphan файлов (без импорта/ссылок), исключая assets"
status: done
epic: v14-dead-code-audit
story: v14-audit-cleanup-waves
complexity: medium
role: null
stack: null
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/audit_orphan_files.py"
  - "tests/test_audit_orphan_files.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-02T11:13:58Z"
---

## Goal

Подготовка волн удаления.

## Acceptance Criteria

1. Отчёт. 2. Список исключений glob. 3. Negative: assets/tests исключены из автоматического delete.

## Plan

## Rollback

## Journal

- 2026-05-02T11:13:58Z [implementation] — AC verified: 1. ✓ scripts/audit_orphan_files.py prints markdown report. 2. ✓ DEFAULT_EXCLUDES tuple covers tests/hooks/__pycache__/.tausik/.claude/.qwen/.cursor/_profile-demo. 3. ✓ Negative: tests excluded — tests/test_audit_orphan_files.py::TestExclusion verifies tests/__pycache__/hooks excluded; doc-mentioned standalone CLI not reported.
