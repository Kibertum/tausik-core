---
slug: r14-rag-reindex-timeout
title: "codebase-rag reindex: progress + soft cancel + per-batch timeout"
status: done
epic: rel-14-readiness
story: rel-14-audit-fixes
complexity: null
role: null
stack: null
tier: moderate
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "agents/claude/mcp/codebase-rag/rag_indexer.py"
  - "agents/cursor/mcp/codebase-rag/rag_indexer.py"
  - "agents/claude/mcp/codebase-rag/server.py"
  - "agents/cursor/mcp/codebase-rag/server.py"
  - "tests/test_rag_reindex_progress.py"
  - "docs/en/mcp.md"
  - "docs/ru/mcp.md"
  - "docs/en/troubleshooting.md"
  - "docs/ru/troubleshooting.md"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-01T01:37:33Z"
---

## Goal

Release 1.4: r14-rag-reindex-timeout (from subagent findings)

## Acceptance Criteria

1. agents/claude/mcp/codebase-rag/rag_indexer.py:index_full accepts max_seconds (soft limit) and progress_every (default 100). 2. Writes '[rag] indexed X/Y files, N chunks, ZZs elapsed' to stderr periodically. 3. Returns truncated=true and partial result when max_seconds exceeded. 4. server.py reindex tool exposes max_seconds param. 5. Mirrored to agents/cursor/mcp/codebase-rag. Negative: progress_every=0 disables logging entirely; tests verify.

## Plan

## Rollback

## Journal

- 2026-05-01T01:37:18Z [implementation] — AC verified: AC-1+2 ✓ tested via tests/test_rag_reindex_progress.py::test_index_full_emits_progress_to_stderr. AC-3 ✓ tested via tests/test_rag_reindex_progress.py::test_index_full_max_seconds_truncates. AC-4 ✓ manual review server.py schema diff. AC-5 mirroring ✓ verified by file copy. Negative: tests/test_rag_reindex_progress.py::test_progress_every_zero_disables_logging.
- 2026-05-01T01:37:18Z [implementation] — Docs: docs/{en,ru}/mcp.md reindex row updated. docs/{en,ru}/troubleshooting.md gained RAG section row covering max_seconds + incremental fallback + stderr progress. Mirrored to .claude/.
- 2026-05-01T01:37:18Z [implementation] — Mirrored claude->cursor for both rag_indexer.py and server.py. Tests tests/test_rag_reindex_progress.py (3 cases) cover stderr emission cadence, max_seconds truncation with mocked time.time, and progress_every=0 silent path.
- 2026-05-01T01:37:18Z [implementation] — rag_indexer.index_full: signature now (project_dir, store, *, max_seconds=None, progress_every=100). Loop emits stderr line every progress_every files; checks elapsed > max_seconds at the top of each iteration; returns extra fields files_total + truncated.
- 2026-05-01T01:37:18Z [implementation] — server.py reindex tool: schema gained max_seconds (integer, minimum 1, full-only). Handler forwards arguments.get('max_seconds') to index_full.
