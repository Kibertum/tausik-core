---
slug: brain-search-timeout-5s
title: "brain_search Notion timeout 30s → 5s"
status: done
epic: v14b-start-token-economy
story: phase-a-quick-wins
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/brain_notion_client.py"
  - "tests/test_brain_notion_client.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-06T16:06:27Z"
---

## Goal

Lower DEFAULT_TIMEOUT in brain_notion_client.py and add SEARCH_TIMEOUT_S read-path constant; brain_search must fail fast.

## Acceptance Criteria

1) brain_notion_client.py has DEFAULT_TIMEOUT <= 10s; 2) separate SEARCH_TIMEOUT_S = 5 used on read-path (search/list); 3) NotionClient accepts timeout kwarg per call so search can override; 4) tests cover that read-path uses 5s timeout

## Plan

## Rollback

## Journal

- 2026-05-06T16:03:38Z [implementation] — Added SEARCH_TIMEOUT_S=5.0; lowered DEFAULT_TIMEOUT 30->10; added timeout kwarg to search(), databases_query(), _request(); 5 new tests pass (38/38 total).
- 2026-05-06T16:04:14Z [implementation] — AC verified: 1) ✓ DEFAULT_TIMEOUT=10.0 (was 30.0); 2) ✓ SEARCH_TIMEOUT_S=5.0 used in search() and databases_query() default path; 3) ✓ NotionClient._request accepts timeout kwarg, search/databases_query expose it; 4) ✓ 5 new tests in test_brain_notion_client.py — read-path uses 5s, override works, default fallback works; pytest 38/38 passed in 0.37s
