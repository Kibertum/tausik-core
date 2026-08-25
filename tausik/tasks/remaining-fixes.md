---
slug: remaining-fixes
title: "Remaining v2.5 fixes: SENAR gaps, N+1, slugify, skills MCP-first, cursor sync"
status: done
epic: null
story: null
complexity: complex
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
completed_at: "2026-03-26T15:52:36Z"
---

## Goal

Закрыть все оставшиеся findings: negative scenario warning, per-criterion AC, N+1 fix, slugify dedup, skills MCP-first, auto-checkpoint, cursor full sync

## Acceptance Criteria

1. QG-0 предупреждает если в AC нет негативного сценария. 2. Per-criterion AC evidence парсинг. 3. graph_resolve_nodes batch queries. 4. _auto_slug вынесен в slugify(). 5. /start, /task, /end skills используют MCP tools. 6. Auto-checkpoint напоминание. 7. Cursor skills полностью синхронизированы. 8. Тесты проходят.

## Plan

[{"step": "Implement all remaining fixes", "done": true}]

## Rollback

## Journal
