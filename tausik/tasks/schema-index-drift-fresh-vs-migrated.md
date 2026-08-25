---
slug: schema-index-drift-fresh-vs-migrated
title: "Индексы расходятся между свежей и мигрированной базой в обе стороны"
status: planning
epic: arch-debt-post-18
story: adp18-quality-signals
complexity: medium
role: architect
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: null
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

## Plan

## Rollback

## Journal
