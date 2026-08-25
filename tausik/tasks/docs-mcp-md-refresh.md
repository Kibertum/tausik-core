---
slug: docs-mcp-md-refresh
title: "MCP.md refresh — 98→103, add 3 missing tools, fix CLI-1:1 claim"
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
completed_at: "2026-05-15T13:35:00Z"
---

## Goal

mcp.md (EN+RU): (1) 'main 98 count' → 103. (2) Добавить tausik_session_open в Sessions, tausik_memory_archive + tausik_memory_dedupe в Memory. (3) Снять или qualify 'MCP mirrors CLI 1:1' — list CLI-only commands. (4) tausik_search params: добавить scope filter.

## Acceptance Criteria

(1) 98 → 103 в mcp.md (EN+RU). (2) tausik_session_open + memory_archive + memory_dedupe добавлены. (3) Drop or qualify 'mirrors CLI 1:1' claim. (4) pnpm build clean. (5) Ошибка: не должно остаться текста с устаревшим '98' и 'mirrors CLI 1:1'.

## Plan

## Rollback

## Journal

- 2026-05-15T13:35:00Z [implementation] — AC verified: '98 count' → 103 (EN), 'mirrors CLI 1:1' переписано с явным списком CLI-only команд (EN+RU), tausik_session_open + tausik_memory_archive + tausik_memory_dedupe добавлены в таблицы Sessions/Knowledge. pnpm build 4.21s clean.
