---
slug: l26-fts-rebuild-missing
title: "FTS-пересборка пропускает fts_task_logs и fts_reasoning_steps"
status: done
epic: landscape-2026-h2
story: l26-hygiene
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths:
  - "scripts/backend_init.py"
  - "tests/test_migrations.py"
scope_tools: []
depends_on: []
completed_at: "2026-07-18T10:49:45Z"
---

## Goal

ЖИВОЙ БАГ КОРРЕКТНОСТИ. backend_init.py:96-103 после миграций пересобирает FTS только для fts_tasks, fts_memory, fts_decisions, fts_specs, fts_adapts, fts_snippets. Пропущены fts_task_logs и fts_reasoning_steps — обе external-content таблицы (backend_schema.py:250-257), которым нужен rebuild после любой миграции, тронувшей контентные таблицы. Следствие: поиск по журналам задач и по RENAR-трейсам молча отдаёт устаревшее/неполное после каждой миграции. Фикс — добавить две таблицы в список. Проверить регресс-тестом: миграция -> поиск по task_logs находит свежую запись.

## Acceptance Criteria

1. fts_task_logs и fts_reasoning_steps добавлены в кортеж пересборки backend_init.py:96 — обе external-content (content=task_logs / content=reasoning_steps, backend_schema.py:250-257), поэтому rebuild им необходим. 2. Регресс-тест в tests/test_migrations.py: БД со старой версией схемы, содержащая запись в task_logs, после миграции находится FTS-поиском. 3. НЕГАТИВНЫЙ СЦЕНАРИЙ доказан конструктивно: при откате фикса тест краснеет — поиск возвращает пустой результат по свежей записи. 4. МЕТА-ГАРД от повторения: тест сверяет кортеж пересборки с фактическим набором external-content FTS-таблиц в схеме и падает, если какая-то таблица отсутствует в списке. 5. ruff чист; полная полоса -m '' по затронутым файлам зелёная на 3.11 и 3.13.

## Plan

## Rollback

git revert; список таблиц возвращается к прежнему

## Journal

- 2026-07-18T10:49:45Z [implementation] — AC-1: ✓ решено сильнее ТЗ — вместо дописывания двух имён список ВЫВОДИТСЯ из sqlite_master (backend_init.external_content_fts_tables), что убирает класс бага целиком: следующая FTS-таблица не потеряется. На живой БД выводит все 8, подтверждено что старый хардкод пропускал ровно fts_task_logs и fts_reasoning_steps. AC-2: ✓ функциональный регресс test_stale_task_log_index_is_repaired_by_rebuild — запись в task_logs, индекс обнулён, после rebuild поиск находит. AC-3: ✓ НЕГАТИВ доказан конструктивно: та же логика со старым хардкод-списком даёт found=0 (индекс остаётся пустым), с новым found=1. AC-4: ✓ мета-гард test_derived_list_misses_no_external_content_index — сверяет выведенный список с объявленными в схеме external-content индексами и падает при отсутствии любого; плюс точечный тест на две исторически забытые таблицы. AC-5: ✓ ruff чист; 58 passed на 3.11 (migrations+fts5_sync+fts_optimize+sanitizer), 30 passed на 3.13; +3 теста -> test_count 4747->4750, реген constants.json и бейджей README, строгий doc-check зелёный. Domain: реальный эффект — поиск по журналам задач и RENAR-трейсам перестаёт молча устаревать после миграций; проверено на живой БД, а не только на синтетике. Checklist: scope соблюдён (backend_init.py + test_migrations.py), тесты покрывают позитив/негатив/мета-гард, security surface нет, rollback = git revert.
