---
slug: v14-pytest-dedupe-audit
title: "Отчёт о потенциальных дублях сценариев pytest"
status: done
epic: v14-test-philosophy
story: v14-test-suite-audit
complexity: medium
role: null
stack: null
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/audit_pytest_dedupe.py"
  - "tests/test_audit_pytest_dedupe.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-02T11:20:24Z"
---

## Goal

Markdown отчёт; ложные срабатывания перечислены.

## Acceptance Criteria

1. Скрипт или ручной аудит с артефактом. 2. Файл отчёта в research/. 3. Negative: известные ложные positives перечислены.

## Plan

## Rollback

## Journal

- 2026-05-02T11:20:09Z [implementation] — AC verified: 1. ✓ scripts/audit_pytest_dedupe.py — AST normalization + signature grouping; --json/--check режимы; 9 тестов в tests/test_audit_pytest_dedupe.py. 2. ✓ Артефакт docs/ru/research/tausik-1.4-pytest-dedupe-2026-05-02.md (164 группы, 480 тестов) — verified by tests/test_audit_pytest_dedupe.py::TestArtifactExists. 3. ✓ Negative: render_markdown содержит секцию «Documented false positives» (idents/strings/numbers стираются нормализатором, parametrize candidates помечаются), tested via TestRenderMarkdown::test_documents_false_positives.
