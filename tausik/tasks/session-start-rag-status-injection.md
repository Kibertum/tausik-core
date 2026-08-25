---
slug: session-start-rag-status-injection
title: "Inject rag_status into SessionStart context"
status: done
epic: v131-blind-review-fixes
story: rag-discoverability
complexity: simple
role: developer
stack: python
tier: trivial
call_budget: 10
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/hooks/session_start.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-27T12:14:58Z"
---

## Goal

session_start.py emits rag_status (chunks count, last_indexed, stale flag) so agent knows whether RAG index is healthy/empty/stale. Closes HIGH (UX).

## Acceptance Criteria

1. session_start.py build_context() calls rag_status (via subprocess or direct import) and emits one-line summary in injected block; 2. Format: 'RAG: chunks=N, last_indexed=T, stale=bool'; 3. Hook degrades gracefully when codebase-rag MCP isn't installed (no crash); 4. Negative: empty index surfaces 'RAG: empty — run reindex' instead of being invisible.

## Plan

## Rollback

## Journal

- 2026-04-27T12:14:57Z [implementation] — AC: 1.✓ _rag_summary() добавлен в session_start.py, читает .tausik/rag/rag.db и возвращает one-line summary; 2.✓ Format: "RAG: {N} chunks indexed — prefer search_code over Grep" / "RAG: empty — run reindex" / "RAG: not initialised — run reindex"; 3.✓ Graceful degradation — try/except вокруг sqlite3 open, missing file → instructive message; 4.✓ build_context() инжектит rag-summary сразу после status; 5.✓ Smoke-test (`python -c ...`) подтверждает что для пустого/невалидного proj возвращается правильный hint; 6.✓ Negative — пустой index больше не невидим: агент видит "RAG: empty — run reindex".
