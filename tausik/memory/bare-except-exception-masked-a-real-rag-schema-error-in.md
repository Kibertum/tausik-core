---
slug: bare-except-exception-masked-a-real-rag-schema-error-in
title: "Bare `except Exception` masked a real RAG schema error in SessionStart"
type: gotcha
tags:
  - issue-2
  - rag
  - session-start
  - silent-error
  - v155
task: v155-fix-rag-table-name
edges: []
---

session_start.py::_rag_summary queried a non-existent table `chunks` (the FTS5 migration in rag_store.py renamed it to `rag_chunks` but never updated this hook). A bare `except Exception` two lines below swallowed the sqlite3.OperationalError and returned a literal 'RAG: status unknown (db unreadable).' on EVERY healthy project — a textbook silent error (violates 'нулевая толерантность к тихим ошибкам'). Agents then saw a fake 'RAG dead' signal and avoided search_code. Fix (issue #2 / upstream PR #3 by GDTuka): query rag_chunks + add a specific `except sqlite3.OperationalError` that surfaces 'RAG: schema error (...)', keeping the generic except only for truly unreadable dbs. LESSON: when renaming a DB table/column, grep the WHOLE tree (hooks included), and never let a broad except hide schema/operational errors behind a generic 'unknown' string — narrow the except so real bugs surface.
