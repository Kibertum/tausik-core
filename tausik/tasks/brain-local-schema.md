---
slug: brain-local-schema
title: "SQLite-схема ~/.tausik-brain/brain.db (FTS5 mirror)"
status: done
epic: shared-brain
story: brain-local-fts
complexity: simple
role: architect
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/brain_schema.py (новый), tests/test_brain_schema.py (новый)"
scope_exclude: "scripts/backend_schema.py и остальной project DB — brain живёт в собственной БД (~/.tausik-brain/brain.db), не смешивать со schema TAUSIK. Никаких миграций TAUSIK-схемы из этой задачи."
relevant_files:
  - "scripts/brain_schema.py"
  - "tests/test_brain_schema.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-22T23:56:01Z"
---

## Goal

Схема: таблицы decisions/web_cache/patterns/gotchas (зеркало Notion properties) + FTS5 virtual tables для полнотекста. Индекс last_edited_time для дельты pull. Meta-таблица sync_state (last_pull_timestamp per category).

## Acceptance Criteria

1) Создан модуль `scripts/brain_schema.py` c константами SCHEMA_VERSION, SCHEMA_SQL, FTS_SQL, FTS_TRIGGERS_SQL, INDEXES_SQL — по аналогии с backend_schema.py. 2) 4 таблицы 1:1 к brain-db-schema.md: brain_decisions, brain_web_cache, brain_patterns, brain_gotchas; PK = notion_page_id TEXT, все properties Notion мапятся на совместимые SQLite-типы (rich_text→TEXT, multi_select→TEXT JSON-array, date→TEXT ISO, number→INTEGER/REAL, checkbox→INTEGER 0/1, select→TEXT). 3) Таблица sync_state (category PK, last_pull_at, last_error, last_error_at). 4) 4 FTS5 virtual table с tokenize='unicode61 remove_diacritics 2' (gotcha §8 из design) и content=<table>, content_rowid=rowid; FTS-триггеры ai/ad/au для каждой. 5) Индексы по last_edited_time (delta-pull), по source_project_hash, по Date (где применимо), по content_hash (web_cache dedup). 6) Unit-test `tests/test_brain_schema.py`: схема применяется к :memory: SQLite, 4 таблицы + sync_state + 4 FTS + все триггеры + все индексы создаются; smoke insert в brain_decisions + FTS-поиск с кириллицей возвращает строку. 7) Gates pass: pytest зелёный, ruff clean на новых файлах. 8) Evidence в task_log: файлы + pytest output + формат «AC verified: N. ... ✓».

## Plan

## Rollback

## Journal

- 2026-04-22T23:53:19Z [implementation] — AC verified: 1. scripts/brain_schema.py создан с SCHEMA_VERSION=1 + SCHEMA_SQL/FTS_SQL/FTS_TRIGGERS_SQL/INDEXES_SQL + apply_schema() ✓ 2. 4 таблицы brain_decisions/brain_web_cache/brain_patterns/brain_gotchas 1:1 к Notion properties; PK id INTEGER AUTOINCREMENT + notion_page_id TEXT UNIQUE; типы: rich_text→TEXT, multi_select→TEXT JSON-array default '[]', date→TEXT, number→INTEGER/REAL, checkbox→INTEGER 0/1 с CHECK, select→TEXT с CHECK enum ✓ 3. sync_state(category PK с CHECK enum, last_pull_at, last_error, last_error_at) ✓ 4. 4 FTS5 virtual table с tokenize='unicode61 remove_diacritics 2' (кириллица проверена test_fts_search_finds_cyrillic ✓), content=<table>, content_rowid='id'; ai/ad/au триггеры для каждой ✓ 5. Индексы: last_edited_time × 4, source_project_hash × 4, date_value × 3, content_hash + fetched_at для web_cache (13 шт) ✓ 6. tests/test_brain_schema.py — 17 тестов, pytest 17/17 passed за 0.09s; проверены: таблицы, FTS, индексы, триггеры, идемпотентность, schema_version, ascii+cyrillic MATCH, delete/update trigger sync, все CHECK constraints (generalizable/confidence/severity/sync_state.category), UNIQUE notion_page_id, NOT NULL web_cache.content_hash, JSON-array defaults ✓ 7. Gates: pytest 17/17 ✓ + ruff check scripts/brain_schema.py tests/test_brain_schema.py → All checks passed ✓ 8. Evidence: 2 новых файла + gotcha #34 (FTS5 дефис — column-qualifier) ✓
