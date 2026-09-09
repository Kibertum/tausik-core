---
slug: post-migration-v43-erases-every-column-added-after-it
title: "Пост-миграция v43 пересобирает tasks по замороженному списку и стирает каждую колонку, добавленную после v43"
status: done
epic: release-19-renar-conformance
story: evidence-and-hygiene-debt-paid-in-19
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: "Не трогать замороженные литералы _CREATE_TASKS_NEW и _TASKS_COLUMNS эпохи v43 — чинится порядок и доприменение, а не снимок схемы"
relevant_files:
  - "scripts/backend_migrations_v43.py"
  - "scripts/backend_schema.py"
  - "tests/test_migration_v43_model_mismatch.py"
scope_paths:
  - "scripts/backend_migrations_v43.py"
  - "scripts/backend_schema.py"
  - "tests/test_migration_v43_model_mismatch.py"
scope_tools: []
depends_on: []
completed_at: "2026-09-09T15:50:17Z"
---

## Goal

ЗАМЕР, смена #241. maybe_rebuild_tasks_v43 вызывается из run_post_migrations, то есть ПОСЛЕ всей версионной петли run_migrations. Он пересобирает tasks по ЗАМОРОЖЕННЫМ _CREATE_TASKS_NEW и _TASKS_COLUMNS эпохи v43. Любая колонка, добавленная миграцией ПОЗЖЕ v43, на этом шаге стирается молча: копирование идёт по явному списку имён, лишняя колонка в него не попадает, а DROP TABLE tasks уносит её вместе со старой таблицей. Воспроизведено на цепочке с v1: run_migrations возвращает 61, tracker_refs из миграции v61 в таблице ОТСУТСТВУЕТ, при этом на свежем пути колонка есть. Порядок вызовов подтверждён трассировкой: четыре перестройки legacy, затем ALTER TABLE tasks ADD COLUMN tracker_refs, затем ПЯТАЯ перестройка из пост-миграций. Живые базы не задеты: _needs_rebuild возвращает 0, когда model_mismatch уже NOT NULL, поэтому у обновлявшейся базы шаг не срабатывает. Задеты те, кто обновляется с базы ДО ужесточения v43 - у них новая колонка исчезает, а код, который на неё рассчитывает, падает на данных. Ловится это только тестом паритета test_schema_upgrade_parity, и поймалось им же - он покраснел на первой колонке, добавленной после v43 за всё время.

## Acceptance Criteria

AC-1 Цепочка с v1 доводит до SCHEMA_VERSION и даёт tasks с ТЕМ ЖЕ набором колонок, что и свежий путь - проверяется на колонке, добавленной ПОСЛЕ v43. AC-2 Заморозка v43 не нарушена: список колонок эпохи v43 остаётся замороженным, чинится ПОРЯДОК или доприменение, а не литерал. AC-3 НЕГАТИВ: у базы, уже прошедшей ужесточение, шаг по-прежнему no-op - проверяется тем, что перестройка не запускается второй раз. AC-4 Тест, который поймал бы это НА ЛЮБОЙ будущей колонке, а не только на tracker_refs: цепочка с v1 сверяется со свежим путём по колонкам tasks.

## Plan

## Rollback

Правится порядок вызова перестройки либо доприменение поздних ALTER после неё; откат - git revert. Данные не трогаются: перестройка и сегодня копирует строки по именам колонок, а её собственный литерал остаётся замороженным.

## Journal

- 2026-09-09T15:34:29Z [implementation] — AC-1: ✓ tests/test_migration_v43_model_mismatch.py::TestПерестройкаНеУноситКолонкиИзПоздних::test_колонка_из_поздней_миграции_переживает_перестройку
- 2026-09-09T15:34:30Z [implementation] — AC-2: ✓ замороженные _CREATE_TASKS_NEW и _TASKS_COLUMNS не тронуты — правка добавляет доприменение ПОСЛЕ перестройки, снимок эпохи v43 остался снимком
- 2026-09-09T15:34:30Z [implementation] — AC-3: ✓ tests/test_migration_v43_model_mismatch.py::TestПерестройкаНеУноситКолонкиИзПоздних::test_повторный_вызов_ничего_не_делает
- 2026-09-09T15:34:30Z [implementation] — AC-4: ✓ tests/test_migration_v43_model_mismatch.py::TestПерестройкаНеУноситКолонкиИзПоздних::test_чинилка_возвращает_ВЫДУМАННУЮ_колонку
- 2026-09-09T15:34:31Z [implementation] — ОТРИЦАТЕЛЬНЫЙ ТЕСТ ОКУПИЛСЯ СРАЗУ: на имени не из ASCII регулярное выражение откатывало необязательную группу COLUMN и захватывало слово COLUMN как имя колонки. Колонка тогда никогда не считалась присутствующей, ALTER повторялся при каждом открытии базы и падал со второго. Имя переведено на \w+.
