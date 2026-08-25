---
slug: v14-artifact-search-ranking
title: "Поиск артефактов: релевантность по стеку"
status: done
epic: v14-brain-snippets
story: v14-brain-snippets-workflow
complexity: medium
role: null
stack: null
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/brain_search.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-01T11:48:36Z"
---

## Goal

Улучшить ranking/filter brain_search для типа artifact.

## Acceptance Criteria

1. Описание правил ранжирования. 2. Тест или fixture на запрос. 3. Negative: пустой query возвращает понятную ошибку 4xx/сообщение.

## Plan

## Rollback

## Journal

- 2026-05-01T11:48:24Z [implementation] — prefer_stack + apply_prefer_stack_ranking; пустой query — warning; docs en/ru brain-search-ranking.md; pytest brain_search + brain_mcp_read + handlers
- 2026-05-01T11:48:33Z [implementation] — AC verified: 1. ✓ docs/en/brain-search-ranking.md + docs/ru/brain-search-ranking.md — правила bm25 + prefer_stack + пустой query. 2. ✓ pytest test_brain_search (ranking), test_brain_mcp_read (prefer_stack + empty query warnings), test_brain_mcp_handlers. 3. ✓ пустой query: handler текст + search_with_fallback warnings.
