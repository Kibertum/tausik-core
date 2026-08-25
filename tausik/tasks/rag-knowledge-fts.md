---
slug: rag-knowledge-fts
title: "RAG: index memory/decisions/dead-ends into FTS5 for faster search"
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

Index knowledge entities (memory, decisions, dead_ends) into rag.db FTS5 tables alongside code. Add scoring/ranking by freshness and type. Estimated 20-30% token savings.

## Acceptance Criteria

1. Knowledge entities (memory, decisions, dead_ends) indexed in FTS5
2. search_knowledge uses FTS5 index instead of backend.search_all
3. Results scored by freshness and type relevance
4. Incremental indexing: new knowledge auto-indexed
5. Tests for indexing and search
6. Empty knowledge base returns no results, not error

## Plan

## Rollback

## Journal
