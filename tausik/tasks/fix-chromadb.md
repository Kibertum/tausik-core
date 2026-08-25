---
slug: fix-chromadb
title: "Убрать ChromaDB dead code или реализовать"
status: done
epic: release-ready
story: p0-blockers
complexity: simple
role: developer
stack: null
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "agents/claude/mcp/codebase-rag/server.py"
  - "agents/claude/mcp/codebase-rag/rag_store_chroma.py"
  - "agents/cursor/mcp/codebase-rag/server.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-03-14T13:04:35Z"
---

## Goal

rag_store_chroma.py импорт работает ИЛИ убран. Нет ImportError при mode=chromadb

## Acceptance Criteria

1. import rag_store_chroma не падает с ImportError | 2. mode=chromadb: работает ИЛИ fallback fts5 с warning | 3. Нет мёртвого кода

## Plan

## Rollback

## Journal
