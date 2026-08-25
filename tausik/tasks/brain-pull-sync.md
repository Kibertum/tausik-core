---
slug: brain-pull-sync
title: "Pull дельты из Notion в local mirror по last_edited_time"
status: done
epic: shared-brain
story: brain-local-fts
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/brain_sync.py (новый), tests/test_brain_sync.py (новый)"
scope_exclude: "Никакого реального сетевого I/O — NotionClient полностью мокается через инъекцию. Не трогать brain_schema.py/brain_notion_client.py/brain_config.py."
relevant_files:
  - "scripts/brain_sync.py"
  - "tests/test_brain_sync.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-23T04:24:02Z"
---

## Goal

Команда `tausik brain sync`. Для каждой database: query Notion с filter last_edited_time > sync_state.last_pull. Upsert в local SQLite. Обновить sync_state. Учесть pagination. Идемпотентно.

## Acceptance Criteria

1) scripts/brain_sync.py создан: open_brain_db(path)→conn (apply_schema внутри), map_page_to_row(category, page_json)→dict (отдельные мапперы на 4 категории), upsert_page(conn, category, row)→None, sync_category(client, conn, database_id, category)→dict{fetched, upserted, last_edited_time}, sync_all(client, conn, database_ids)→dict{category→result}. 2) Mapping Notion property-типов: title/rich_text → concat all .plain_text; multi_select → JSON-array of names; select → .name or None; date → .start or None; checkbox → 1/0; url → str or None; number → value. 3) sync_category формирует filter {timestamp:'last_edited_time', last_edited_time:{'on_or_after': sync_state.last_pull_at}} если last_pull_at есть, иначе без filter; sorts по last_edited_time asc; iter_database_query даёт автопагинацию. 4) upsert_page: INSERT OR REPLACE по notion_page_id; все 14-16 полей на категорию. 5) После успешного прогона sync_category обновляет sync_state: last_pull_at = max(last_edited_time из batch), last_error=NULL. При исключении — last_error=str(e), last_error_at=timestamp, исключение пробрасывается. 6) sync_all проходит по 4 категориям, продолжает даже если одна категория упала (result содержит error на неё). 7) tests/test_brain_sync.py: маппинг всех 4 категорий (данные всех Notion-типов), пустая БД → pull всех, incremental filter с last_pull_at, upsert дубликата, обновление sync_state, ошибка записывает last_error, sync_all исполняет 4 категории. 8) Gates: pytest + ruff зелёные; <400 строк модуль. 9) Evidence в task_log с «AC verified: N. ... ✓».

## Plan

## Rollback

## Journal

- 2026-04-23T04:21:09Z [implementation] — AC verified: 1. scripts/brain_sync.py (305 строк): open_brain_db/map_page_to_row/upsert_page/sync_category/sync_all + приватные мапперы на 4 категории + _get/_update_sync_state ✓ 2. Mapping Notion → row покрывает title+rich_text (concat plain_text), multi_select (JSON-array of names), select (.name or None), date (.start), checkbox (1/0, default 1 для Generalizable), url, number — все проверено в test_map_decision/_web_cache/_pattern_and_gotcha ✓ 3. sync_category: без last_pull_at → filter=None (test_sync_category_empty_db_pulls_without_filter); с last_pull_at → filter={timestamp:'last_edited_time', last_edited_time:{on_or_after: X}} (test_second_run_uses_last_pull_at_filter); sorts=ascending всегда; iter_database_query вызывается для автопагинации ✓ 4. upsert_page: INSERT OR REPLACE, подтверждено что повторный page.id обновляет, не дублирует (test_sync_category_upserts_same_page_id — 1 строка, name='Rewritten') ✓ 5. sync_state после success: last_pull_at = max edited_time, last_error=NULL (test_sync_category_updates_sync_state_on_success). При ошибке: last_error=str(e), last_error_at=now, raise (test_sync_category_records_error_and_reraises); commit перед raise чтобы ошибка сохранилась ✓ 6. sync_all: 4 категории, missing database_id → результат содержит error (test_sync_all_reports_missing_database_id); ошибка в одной не останавливает другие (test_sync_all_continues_after_one_category_fails — decisions fails, остальные 3 успешно пусты) ✓ 7. tests/test_brain_sync.py — 15 тестов, 15/15 за 0.64s. Регресс brain-suite 78/78 (schema+config+client+sync) ✓ 8. Gates: ruff All checks passed, filesize 305 < 400 ✓ 9. Edge: пустая БД на пустом pull — last_pull_at остаётся NULL (test_sync_category_empty_result_leaves_last_pull_at_none) — можно пересинхронизировать полностью
