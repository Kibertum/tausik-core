---
slug: docs-architecture-counts-refresh
title: "Architecture.md count refresh — schema v27, 25 gates, 137 files, 3378 tests"
status: done
epic: null
story: null
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-15T13:29:07Z"
resolution: null
resolution_reason: null
tracker_refs: []
started_model_id: null
started_model_version: null
done_model_id: null
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
---

## Goal

architecture.md (EN+RU): Schema v18 → v27 на 3 местах, 16 gates → 25 + 9 missing names, 117 → 137 source files, 2590 → 3378 tests. Также senar-compliance-matrix counts: 100 tools → 103, 19 hooks → 20.

## Acceptance Criteria

(1) Все числовые правки соответствуют constants.json или прямому подсчёту в коде. (2) pnpm build clean. (3) Содержание не утеряно. (4) Ошибка: не должно остаться никаких устаревших чисел/имён.

## Plan

## Rollback

## Journal

- 2026-05-15T13:29:06Z [implementation] — AC verified: правки сделаны, pnpm build clean 4.63s.
