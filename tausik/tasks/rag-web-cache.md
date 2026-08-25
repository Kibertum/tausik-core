---
slug: rag-web-cache
title: "RAG: web search cache table + FTS5 for token savings"
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
completed_at: null
---

## Goal

Add web_cache table to rag.db with FTS5 indexing. MCP tool search_web_cache checks cache before web search. Estimated 60-80% savings on repeated queries.

## Acceptance Criteria

1. web_cache table in rag.db with FTS5 virtual table
2. store_web_result(url, query, content, ttl_hours) function
3. search_web_cache(query) returns cached results if fresh
4. MCP tool cache_web_result for storing
5. MCP tool search_web_cache for querying (cache-first, fallback info)
6. TTL expiration: stale results marked, not returned by default
7. Tests for store, search, expiration
8. Empty cache returns no results, not error

## Plan

## Rollback

## Journal

- 2026-04-08T13:45:17Z [implementation] — AC verified: 1. web_cache table with FTS5 in rag_web_cache.py ✓ 2. store() function ✓ 3. search() with TTL filtering ✓ 4. MCP cache_web_result tool ✓ 5. MCP search_web_cache tool ✓ 6. TTL expiration + cleanup_stale() ✓ 7. 15 tests pass ✓ 8. Empty cache returns empty list ✓
