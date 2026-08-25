---
slug: fix-mypy-commit-gate-tx-method-stubs-count-guard-i
title: "Fix mypy commit-gate: tx-method stubs + COUNT guard in backend_events_chain"
status: done
epic: null
story: null
complexity: null
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/backend_events_chain.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-13T20:19:16Z"
---

## Goal

Pre-commit mypy блокирует коммит v16r-audit-hashchain: begin_tx/commit_tx/rollback_tx отсутствуют в TYPE_CHECKING-стабах BackendEventsChainMixin + _q1 COUNT result не индексируется. Добавить стабы и guard.

## Acceptance Criteria

1. mypy проходит на scripts/backend_events_chain.py (0 errors). 2. Полный pre-commit (mypy) зелёный → коммит проходит. 3. tx-стабы (begin_tx/commit_tx/rollback_tx) в TYPE_CHECKING; COUNT-результат guard'ится от None.

## Plan

## Rollback

## Journal

- 2026-06-13T20:18:59Z [implementation] — AC1 ✓ mypy success no issues (backend_events_chain.py). AC2 ✓ pre-commit mypy 169 files OK, commit 214a035 прошёл. AC3 ✓ begin_tx/commit_tx/rollback_tx стабы добавлены, COUNT guard count_row if else 0. test_events_chain 12/12.
- 2026-06-13T20:19:15Z [implementation] — AC1-3 ✓ mypy success (169 files), commit 214a035 прошёл, стабы+guard добавлены, test_events_chain 12/12. Domain: type-only фикс, поведение идентично.
