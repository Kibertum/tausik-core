---
slug: fix-mcp-paths
title: "Исправить хардкод путей в MCP серверах"
status: done
epic: docs-audit
story: templates-sync
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "agents/claude/mcp/web-cache/server.py"
  - "agents/claude/mcp/codebase-rag/server.py"
  - "agents/cursor/mcp/web-cache/server.py"
  - "agents/cursor/mcp/codebase-rag/server.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-03-14T12:49:52Z"
---

## Goal

MCP web-cache server.py хардкодит .claude/scripts для sys.path — унифицировать поиск scripts/

## Acceptance Criteria

1. web-cache server.py не хардкодит .claude/scripts
2. Ищет scripts/ через __file__ (рядом с собой) или через .frai/
3. Работает и из .claude/ и из .cursor/ директорий
4. RAG server.py аналогично проверен

## Plan

## Rollback

## Journal
