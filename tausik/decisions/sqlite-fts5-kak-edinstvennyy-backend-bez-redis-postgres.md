---
slug: sqlite-fts5-kak-edinstvennyy-backend-bez-redis-postgres
task: null
date: "2026-03-14"
edges: []
---

## Decision

SQLite + FTS5 как единственный backend. Без Redis, Postgres, ChromaDB.

## Rationale

Zero-dependency philosophy. Один файл .frai/frai.db — проще бекапить, переносить, дебажить. FTS5 покрывает 95% поисковых задач.
