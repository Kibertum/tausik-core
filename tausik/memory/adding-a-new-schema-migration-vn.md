---
slug: adding-a-new-schema-migration-vn
title: "Adding a new schema migration (vN)"
type: convention
tags:
  - "migration,schema,fts5,filesize"
task: null
edges: []
---

When adding migration vN with a new FTS5 content table: (1) mirror the DDL in BOTH backend_schema_*.py (fresh-DB path, run by init_schema) AND backend_migrations_vN.py (existing-DB path) — a test must assert structural+DDL-body equivalence; (2) add the new fts_* table to the post-migration FTS rebuild loop in backend_init.py (precedent: fts_specs/fts_adapts/fts_snippets) even though a freshly-created table is empty; (3) bump SCHEMA_VERSION in backend_schema.py and register vN in backend_migrations._CURRENT_MIGRATIONS; (4) backend_migrations.py sits near the 400-line filesize gate — adding a vN entry can tip it over; post-migration seeding lives in backend_migrations_postseed.py, keep new logic out of the registry file. See snippets table (v37, v15-snippet-table).
