---
slug: brain-sync-sql-whitelist-cols
title: "HIGH: whitelist колонок в upsert_page вместо f-string SQL"
status: done
epic: null
story: null
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: brain-decide-auto-route
scope: "scripts/brain_sync.py, tests/test_brain_sync.py"
scope_exclude: "brain_schema.py (source of truth, не меняется), brain_mcp_read.py, все FTS SQL"
relevant_files:
  - "scripts/brain_sync.py"
  - "tests/test_brain_sync.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-24T11:16:10Z"
---

## Goal

Закрыть injection-adjacent path: cols из row.keys() интерполируются в SQL. Ввести whitelist колонок per category (hardcoded) или quote через [col]

## Acceptance Criteria

AC1: _ALLOWED_COLS_OF[category] — dict[str, frozenset[str]] в scripts/brain_sync.py с точным списком колонок каждой brain_* таблицы.
AC2: upsert_page() фильтрует row.keys() через whitelist: unknown column raises ValueError с именем колонки.
AC3: f-string SQL формируется ТОЛЬКО из whitelisted column names.
AC4: Новый тест: upsert_page(category='decisions', row={'notion_page_id':..., 'DROP TABLE foo--':'x'}) raises ValueError.
AC5: Новый тест: валидный row (все cols из schema) сохраняется без ошибки.
AC6: Существующие тесты test_brain_sync.py остаются зелёными.
AC7: ruff + mypy scripts/ clean.

## Plan

## Rollback

## Journal

- 2026-04-24T11:12:45Z [implementation] — AC verified: 1. _ALLOWED_COLS_OF dict с 4 frozenset'ами (decisions, web_cache, patterns, gotchas) ✓ 2. upsert_page фильтрует row.keys() через whitelist, raises ValueError с sorted(unknown) ✓ 3. f-string SQL формируется из whitelisted col_list (cols проходят фильтр allowed) ✓ 4. test_upsert_page_rejects_unknown_column с 'DROP TABLE brain_decisions--' → ValueError ✓ 5. test_upsert_page_accepts_schema_exact_columns (полный row) + test_upsert_page_accepts_subset_of_columns (row без DB-default columns) оба зелёные ✓ 6. 19/19 brain_sync tests pass (10 существующих + 4 новых, 5 existing удалены из подсчёта — на самом деле 15 existing + 4 новых) ✓ 7. ruff + mypy scripts/ clean ✓ 8. Regression: test_brain_mcp_write + test_brain_mcp_read + test_brain_search = 86/86 pass ✓
- 2026-04-24T11:12:48Z [implementation] — Root cause: upsert_page формировал SQL через f-string где table валидировался через _TABLE_OF[category] (safe), но cols брался как row.keys() без whitelist. _map_* мапперы сейчас контролируют ключи, но если будущий маппер примет external input (напр. pass-through custom properties из Notion) — cols могут попасть под контроль злоумышленника. Защита: 4 frozenset'а с точным schema, unknown → ValueError.
