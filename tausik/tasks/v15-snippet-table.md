---
slug: v15-snippet-table
title: "Dedicated snippets table в .tausik/tausik.db + миграция"
status: done
epic: v15-snippet-system
story: v15-snippet-foundation
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/backend_schema_snippets.py (new SNIPPETS_SQL), scripts/backend_migrations_v37.py (new MIGRATION_V37), scripts/backend_init.py (wire SNIPPETS_SQL on fresh path), scripts/backend_migrations.py (register v37), scripts/backend_schema.py (SCHEMA_VERSION 36->37), scripts/snippet_storage.py (new CRUD), tests/test_snippet_storage.py (new)"
scope_exclude: "AST detection/clustering (v15-snippet-ast-detect), classifier detect_artifact_kind (v15-snippet-classifier), MCP snippet_search tool, CLI snippet command — table+storage layer only"
relevant_files:
  - "scripts/backend_schema_snippets.py"
  - "scripts/backend_migrations_v37.py"
  - "scripts/backend_migrations_postseed.py"
  - "scripts/snippet_storage.py"
  - "scripts/backend_init.py"
  - "scripts/backend_migrations.py"
  - "scripts/backend_schema.py"
  - "tests/test_snippet_storage.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-13T22:47:01Z"
---

## Goal

Закрыть оговорку из docs/en/brain-artifact-taxonomy.md backlog ('a dedicated snippets DB is backlog'). Создать таблицу snippets в .tausik/tausik.db с полями: id, hash (для dedup), language, code, source_file, source_lines, taxonomy_kind, created_at, fts_rank. FTS5 виртуальная таблица для full-text. Миграция на старте (idempotent). CRUD helpers в scripts/snippet_storage.py. Tests: схема, миграция, CRUD, FTS5 search. Это (2/5) v15 snippet system — нужно перед AST-detector (он пишет в эту таблицу).

## Acceptance Criteria

1. snippets table + fts_snippets (FTS5) + ai/ad/au triggers created on BOTH fresh-DB path (init_schema) and migration v37 path (existing DB); SCHEMA_VERSION bumped 36->37; fresh-DB and migrated schemas are structurally equivalent. 2. scripts/snippet_storage.py CRUD: add_snippet (dedup by hash), get_snippet, get_by_hash, search_snippets (FTS5), delete_snippet, count_snippets. 3. NEGATIVE: re-adding a snippet with an existing hash creates NO 2nd row and returns the original id; search for a non-indexed term returns [] (not error); get_snippet(missing_id) returns None; delete_snippet(missing_id) is a no-op (no raise). 4. tests/test_snippet_storage.py covers schema presence, fresh-vs-migration equivalence, CRUD, FTS5 search, dedup guard; full pytest green; doc constants regenerated.

## Plan

## Rollback

git revert the single commit. Migration v37 is purely additive (new tables only, no ALTER, IF NOT EXISTS) — no data loss. Rollback safe pre-release only: per repo policy migrations are irreversible, so a DB already at v37 would trip the 'schema newer than code' guard after revert; acceptable as no production DB reaches v37 before this ships.

## Journal

- 2026-06-13T22:44:20Z [implementation] — Verification-checklist (QG-2, medium): scope=snippets table+FTS5+CRUD only, no AST/classifier/MCP/CLI (deferred tasks). tests=tests/test_snippet_storage.py 15 passed (schema presence, fresh-vs-migration object+DDL-body equivalence, CRUD, FTS5 search, dedup-by-hash, delete/update FTS resync); regression backend/migration/schema 267 passed; ruff+mypy clean. security=parameterized SQL only; _COLUMNS is a fixed module constant (f-string interp safe, no user input); _fts_quote neutralizes FTS5 operator chars into a literal phrase (no injection/raise); INSERT OR IGNORE+reselect removes TOCTOU on concurrent ingest. edge-cases=dedup returns original id (no 2nd row), missing id->None, delete missing->no-op, empty query->[], no-match->[], limit clamped [1,200], au-trigger keeps FTS synced on UPDATE. Domain: on a real v36->v37 upgrade the snippets table+fts are created empty and added to the post-migration FTS rebuild loop (consistent with fts_specs/fts_adapts precedent); ongoing sync via triggers.
- 2026-06-13T22:44:28Z [implementation] — AC verified: 1.✓ snippets+fts_snippets+3 triggers+2 indexes on BOTH fresh path (test_fresh_db_has_all_objects) and migration v37 (test_migration_v37_matches_fresh — object names AND normalized DDL bodies equal); SCHEMA_VERSION 36->37 (test_schema_version_bumped, test_fresh_db_records_version). 2.✓ snippet_storage CRUD all covered (add/get/get_by_hash/search/delete/count). 3.✓ NEGATIVE dedup test_dedup_by_hash (same hash->same id, count==1), get_missing->None, delete missing->False no-raise, empty/no-match search->[]. 4.✓ tests/test_snippet_storage.py 15 passed; regression 267 passed; ruff+mypy+check_docs green; constants+README regenerated to 3975.
- 2026-06-13T22:47:01Z [implementation] — AC verified: 1.✓ snippets+fts_snippets+3 triggers+2 indexes on BOTH fresh path and migration v37 (object names AND normalized DDL bodies equal); SCHEMA_VERSION 36->37. 2.✓ CRUD add/get/get_by_hash/search/delete/count covered. 3.✓ NEGATIVE dedup (same hash->same id, count==1), missing->None, delete-missing->no-op, empty/no-match search->[]. 4.✓ test_snippet_storage 15 passed; regression 324 passed (incl v18-seed after backend_migrations refactor); ruff+mypy+check_docs green; constants/README=3975. Reviewer round-2: 2 CRIT fixed (INSERT OR IGNORE+reselect removes lastrowid-None crash & TOCTOU; fts_snippets added to post-migration rebuild loop); filesize gate forced cohesive extraction of post-migration seeding into backend_migrations_postseed.py (406->369).
