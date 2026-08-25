---
slug: v155-fix-rag-table-name
title: "Fix issue #2: SessionStart RAG queries wrong table (chunks→rag_chunks)"
status: done
epic: v155-kilo-zai
story: v155-kilo-bootstrap
complexity: simple
role: developer
stack: python
tier: light
call_budget: 15
defect_of: v155-fix-provider-scaffold
scope: null
scope_exclude: null
relevant_files:
  - "scripts/hooks/session_start.py"
  - "tests/test_session_start_hook.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-19T08:49:08Z"
---

## Goal

Apply PR #3: fix chunks→rag_chunks + surface schema OperationalError instead of swallowing it (silent-error violation).

## Acceptance Criteria

1. session_start.py _rag_summary queries rag_chunks (not chunks). 2. A real schema error (OperationalError) is surfaced as 'RAG: schema error (...)' not hidden behind the generic 'db unreadable' swallow. 3. On a healthy index, the summary reports the real chunk count. NEGATIVE: a genuinely unreadable/corrupt db still returns the generic 'status unknown (db unreadable)' (generic except retained for non-schema errors); missing rag.db path still spawns full reindex (unchanged).

## Plan

## Rollback

git checkout scripts/hooks/session_start.py — single-file two-line change.

## Journal

- 2026-06-19T08:48:49Z [implementation] — AC1 ✓ _rag_summary now queries rag_chunks (verified vs rag_store.py:14 CREATE TABLE rag_chunks). AC2 ✓ sqlite3.OperationalError surfaced as 'RAG: schema error (...)' — tests/test_session_start_hook.py::TestRagSummary::test_schema_error_is_surfaced_not_hidden. AC3 ✓ healthy index reports count — ::test_healthy_index_reports_count (42 chunks). NEGATIVE ✓ generic except retained for non-schema errors (db unreadable); missing rag.db path unchanged. 13 hook tests pass, ruff clean. Root cause: the chunks→rag_chunks rename in rag_store.py (FTS5 migration) never updated the SessionStart hook; a bare except Exception masked the OperationalError as a fake 'db unreadable' on every healthy project. Fix mirrors upstream PR #3 (GDTuka). Domain: agents now see the real RAG chunk count and are correctly steered to search_code instead of a false 'RAG dead' signal.
- 2026-06-19T08:49:08Z [implementation] — AC1-3 + negatives verified (see prior log); 13 hook tests pass incl. TestRagSummary (healthy count + schema error surfaced). Knowledge: gotcha Memory #179. Root cause: FTS5 rename chunks→rag_chunks never propagated to the hook; bare except masked the OperationalError. Mirrors upstream PR #3.
- 2026-06-19T08:49:14Z [done] — Root cause (regression): FTS5 migration renamed the RAG table chunks→rag_chunks in rag_store.py but never updated session_start.py::_rag_summary, and a bare `except Exception` masked the resulting OperationalError as a fake 'db unreadable'. Prevention: on any table/column rename, grep the whole tree (hooks included) for the old name; narrow broad excepts so schema/operational errors surface instead of degrading to a generic 'unknown' string. Regression test added (TestRagSummary).
