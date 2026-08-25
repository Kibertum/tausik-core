---
slug: fts5-full-text-search
title: "FTS5 full-text search"
type: pattern
tags:
  - fts5
  - search
  - sqlite
task: null
edges: []
---

5 FTS5 virtual tables: fts_tasks, fts_memory, fts_web_cache, fts_decisions, fts_plans. Auto-synced via INSERT/UPDATE/DELETE triggers in backend_schema.py. search_all() queries all scopes or a specific one. FTS uses SQLite content-sync mode (content='table', content_rowid='id').
