---
slug: search-integration
title: "Интеграция code search и task search"
status: done
epic: release-ready
story: p1-value
complexity: medium
role: developer
stack: null
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "agents/claude/mcp/codebase-rag/server.py"
  - "agents/cursor/mcp/codebase-rag/server.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-03-14T13:14:08Z"
---

## Goal

search_code возвращает связанные задачи. search_knowledge возвращает связанный код

## Acceptance Criteria

1. search_code возвращает relevant_tasks[] | 2. search_knowledge возвращает code_refs[] | 3. MCP server обновлён | 4. Тест на cross-search

## Plan

## Rollback

## Journal
