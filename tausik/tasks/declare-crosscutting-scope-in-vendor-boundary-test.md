---
slug: declare-crosscutting-scope-in-vendor-boundary-test
title: "declare CROSSCUTTING_SCOPE in vendor boundary test"
status: done
epic: null
story: null
complexity: null
role: qa
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "tests/test_bootstrap_vendor.py"
scope_paths: []
scope_tools: []
assurance_profiles: []
assurance_impact: null
depends_on: []
completed_at: "2026-10-08T09:18:17Z"
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
blocked_question: null
unblock_criteria: null
unblocked_by: null
unblocked_at: null
---

## Goal

Реестр crosscutting требует от нового test_bootstrap_vendor.py объявления области итерации дерева; добавить одну строку, вернуть полный лейн в зелёный.

## Acceptance Criteria

1. tests/test_bootstrap_vendor.py объявляет CROSSCUTTING_SCOPE = ['.tausik/vendor'] — реестр перестаёт видеть его слепым к scoped-pytest гейту.
2. НЕГАТИВНЫЙ: без объявления тест_crosscutting краснеет (проверено живым прогоном 13102 passed / 1 failed до правки).

## Plan

## Rollback

## Journal

- 2026-10-08T09:13:13Z [implementation] — AC-1: AC CROSSCUTTING_SCOPE declared: tests/test_bootstrap_vendor.py несет CROSSCUTTING_SCOPE = ['.tausik/vendor']; тесты файла 5 passed + реестр 10 passed. AC-2 NEGATIVE: живой прогон до правки - 13102 passed / 1 failed (test_new_tree_iterator_must_declare_or_optout называл файл слепым). Полный лейн после: 13103 passed / 37 skipped / 0 failed / 0 deselected.
