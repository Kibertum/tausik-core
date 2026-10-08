---
slug: brain-search-defensive-timeout
title: "brain_mcp_read.search defensive timeout handling"
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
  - "scripts/brain_mcp_read.py"
  - "tests/test_brain_mcp_read.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-06T16:07:45Z"
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

On Notion timeout/network error: return empty results + warning, never propagate exception that could block /start.

## Acceptance Criteria

1) brain_mcp_read.search catches NotionNetworkError/timeout and returns local results + warning; 2) brain_mcp_read.search catches generic urllib timeout (wrapped in NotionNetworkError) without exception; 3) tests prove timeout path returns local results + warning, no exception

## Plan

## Rollback

## Journal

- 2026-05-06T16:07:40Z [implementation] — Defensive handling already exists in search_with_fallback (try/except Exception → brain_fallback.classify_error). Added test_search_fallback_notion_network_error_classified_as_offline that injects NotionNetworkError directly and asserts: 1) no propagation, 2) local results returned, 3) warning has offline/local-mirror/network keyword. AC verified: 1) ✓ search_with_fallback already catches NotionNetworkError via except Exception (brain_mcp_read.py:198); 2) ✓ urllib.URLError wraps to NotionNetworkError in brain_notion_client._request, then caught; 3) ✓ new test passes (30/30 in test_brain_mcp_read.py)
- 2026-09-26T18:44:22Z [done] — EVIDENCE-RETIRED: test_brain_mcp_read.py — file deleted by 77703c4a (feat(knowledge)!: remove the Notion transport); cited without its directory
