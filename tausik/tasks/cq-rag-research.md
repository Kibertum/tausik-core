---
slug: cq-rag-research
title: "Research Mozilla CQ + optimize codebase RAG for token savings"
status: done
epic: null
story: null
complexity: complex
role: architect
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

Explore Mozilla CQ (https://github.com/mozilla-ai/cq) for web search caching in SQLite. Evaluate integration into TAUSIK core. Also audit existing codebase-rag to ensure FTS5 indexes are effective and reduce generic file scanning.

## Acceptance Criteria

1. Mozilla CQ explored: architecture, capabilities, SQLite integration
2. Existing codebase-rag audited: FTS5 effectiveness, index coverage
3. Decision recorded: integrate CQ, build own, or enhance existing
4. If integrating: implementation plan with files and complexity
5. Token savings estimated
6. CQ incompatible (wrong deps, etc.) results in dead-end doc, not silent skip

## Plan

## Rollback

## Journal

- 2026-04-08T12:43:42Z [implementation] — AC verified: 1. CQ explored — inter-agent knowledge sharing, not web cache ✓ 2. RAG audited — FTS5 code search works, knowledge search via backend.search_all, gaps: no web cache, no scoring ✓ 3. Decision #29: enhance existing FTS5, don't integrate CQ SDK ✓ 4. Plan: web_cache table + knowledge FTS + search scoring ✓ 5. Estimated 40-60% token savings ✓ 6. CQ SDK incompatible (pydantic+httpx deps) — documented ✓
