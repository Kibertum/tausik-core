---
slug: indeksy-na-migration-added-kolonki-ne-v-base-indexes-sql
title: "Индексы на migration-added колонки НЕ в base INDEXES_SQL"
type: gotcha
tags:
  - gotcha
  - indexes
  - init
  - migration
  - schema
task: v16r-model-pinning
edges: []
---

init_schema порядок: SCHEMA_SQL → FTS → INDEXES_SQL → migrations. На СУЩЕСТВУЮЩЕЙ БД CREATE TABLE IF NOT EXISTS — no-op (новая колонка НЕ добавляется), а INDEXES_SQL бежит ДО run_migrations. Поэтому CREATE INDEX на колонку, добавляемую миграцией (started_model_id, model_mismatch — v33), КРАШИТ init_schema 'no such column' на апгрейде. Прецедент: idx_tasks_archived_at (v25) живёт ТОЛЬКО в миграции. Правило: индексы на новые колонки существующих таблиц — ТОЛЬКО в миграции (fresh DB их недополучит — perf-only, ок). Индексы на новые ТАБЛИЦЫ (reasoning_steps v32) можно в INDEXES_SQL — SCHEMA_SQL создаёт таблицу через IF NOT EXISTS до индексов. Поймано verify-прогоном на живой БД (v16r-model-pinning).
