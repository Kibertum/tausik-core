---
slug: schema-index-drift-fresh-vs-migrated
title: "Индексы расходятся между свежей и мигрированной базой в обе стороны"
status: done
epic: release-110-deferred-from-19
story: release110-site-docs-and-hygiene
complexity: medium
role: architect
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/backend_schema_indexes.py"
  - "tests/test_schema_index_parity.py"
scope_paths:
  - "scripts/backend_schema_indexes.py"
  - "tests/test_schema_index_parity.py"
  - "CHANGELOG*.md"
scope_tools: []
depends_on: []
completed_at: "2026-09-23T23:18:23Z"
---

## Goal

НАБЛЮДЕНИЕ, замерено в сессии #159 при работе над v2-verify-receipt-as-argument. Свежая база (init_schema) и база, поднятая миграциями с v1, расходятся по индексам В ОБЕ СТОРОНЫ. Замер:

ТОЛЬКО У СВЕЖЕЙ: idx_decisions_task_slug, idx_memory_task_slug, idx_memory_type, idx_stories_epic_id, idx_stories_status.
ТОЛЬКО У МИГРИРОВАННОЙ: idx_brain_events_session, idx_brain_events_ts, idx_brain_events_type, idx_memory_archived_at, idx_reviews_task, idx_reviews_type, idx_sessions_model, idx_usage_events_tool.

ПРИЧИНА, УЖЕ ЧАСТИЧНО НАЙДЕННАЯ. Индекс живёт ЛИБО в INDEXES_SQL (применяется ДО миграций, значит только колонки базовой линии v1), ЛИБО внутри своей миграции (значит на свежей базе не создаётся никогда, потому что init_schema штампует текущую версию и run_migrations не применяет ничего). Обе половины верны одновременно, поэтому в 1.8 добавлен третий носитель — POST_MIGRATION_INDEXES_SQL, применяемый ПОСЛЕ миграций на обоих путях. Он закрывает семь индексов, названных явно, и НЕ закрывает расхождение выше.

ОТДЕЛЬНАЯ НАХОДКА ТОГО ЖЕ КЛАССА: миграция v43 перестраивает таблицу tasks и пересоздаёт её индексы из ЗАМОРОЖЕННОГО списка, составленного до v41. Поэтому idx_tasks_no_file_changes_declared, добавленный в v41, ронялся перестройкой и не существовал НИ НА ОДНОЙ базе, прошедшей v43. Сейчас он восстановлен через POST_MIGRATION_INDEXES_SQL, но сама форма дефекта — «перестройка таблицы копирует список индексов на момент своего написания» — жива и повторится при следующей перестройке.

ЧТО СДЕЛАТЬ. Не чинить перечислением: закрывать ФОРМУ (конвенция #361). Кандидат — единый источник текущего набора индексов плюс гейт, сравнивающий индексы свежей и мигрированной базы, как test_schema_upgrade_parity делает для КОЛОНОК. Гейт уже наполовину есть: tests/test_schema_index_parity.py, сознательно суженный до семи индексов POST_MIGRATION_INDEXES_SQL, потому что полное сравнение красное по причинам, предшествующим 1.8.

ПОСЛЕДСТВИЕ СЕГОДНЯ — производительность, не корректность: SQLite отрабатывает запросы и без индекса. Поэтому задача не в 1.8.

## Acceptance Criteria

1. Re-measured before any change: which indexes differ between a fresh and a migrated database today, in each direction, and whether same-named indexes differ in definition. 2. The CURRENT index set is stated once: every index a migration creates is also in POST_MIGRATION_INDEXES_SQL, so both paths carry it. 3. NEGATIVE: tests/test_schema_index_parity.py compares the FULL sets both ways and the definitions (whitespace-normalised), so the next index added only inside a migration, or dropped by a table rebuild from a frozen list (the v43 form), turns it red; checked by a mutation. 4. Stated, not hidden: a database that is already at the head version when it gets this code skips DDL (init_schema early return), so a fresh-born database gains the missing indexes at the next schema bump; consequence is performance only.

## Plan

## Rollback

git revert; the added statements are CREATE INDEX IF NOT EXISTS, so a reverted build leaves harmless extra indexes behind

## Journal

- 2026-09-23T23:17:07Z [implementation] — AC-1: ✓ measurement — re-measured session #269 (probe: fresh init_schema vs V1_SCHEMA carried up by run_migrations then init_schema, as the parity fixture does): fresh-only NONE (the five of session #159 were fixed since); migrated-only 12: idx_brain_events_session/_ts/_type, idx_memory_archived_at, idx_redactions_at/_entity, idx_reviews_task/_type, idx_sessions_model, idx_task_deps_on/_task, idx_usage_events_tool. Same-named with different text: 4, all whitespace only. Tables identical on both paths.
- 2026-09-23T23:18:05Z [implementation] — Root cause: an index created only inside its migration never reaches a fresh database (init_schema stamps the head version, run_migrations applies nothing), and the parity test was deliberately scoped to the seven post-migration indexes, so the other twelve drifted unobserved.
- 2026-09-23T23:18:06Z [implementation] — AC-2: ✓ tests/test_schema_index_parity.py::TestFreshAndMigratedCarryTheSameIndexes::test_no_index_exists_on_one_path_only — the twelve migration-only indexes are appended to POST_MIGRATION_INDEXES_SQL (IF NOT EXISTS), the block now states the current set.
- 2026-09-23T23:18:06Z [implementation] — AC-3: ✓ tests/test_schema_index_parity.py::TestFreshAndMigratedCarryTheSameIndexes::test_same_named_indexes_are_defined_alike — negative, full two-way sets plus whitespace-normalised definitions; mutation (idx_reviews_type removed from the block) went red with ([], ['idx_reviews_type']); restored. 106 schema/migration tests pass.
- 2026-09-23T23:18:06Z [implementation] — AC-4: ✓ review — stated in the block comment, CHANGELOG EN/RU and here: init_schema returns early at the head version, so a database born fresh before this change gains the twelve at the next schema bump (no bump made for a performance-only fix).
