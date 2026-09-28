---
slug: a-table-added-only-as-a-migration-is-absent-from-e
title: "a table added only as a migration is absent from every fresh install"
status: done
epic: null
story: null
complexity: null
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/backend_schema_red_history.py"
  - "scripts/backend_init.py"
  - "scripts/renar_tc_premise.py"
  - "tests/test_fresh_install_has_every_migrated_table.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - ROADMAP.md
scope_paths:
  - "scripts/backend_schema_red_history.py"
  - "scripts/backend_init.py"
  - "scripts/renar_tc_premise.py"
  - "tests/test_fresh_install_has_every_migrated_table.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - ROADMAP.md
scope_tools: []
depends_on: []
completed_at: "2026-09-08T20:23:55Z"
resolution: null
resolution_reason: null
tracker_refs: []
started_model_id: claude-opus-5
started_model_version: null
done_model_id: claude-opus-5
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
---

## Goal

НАЙДЕНО ПРОВЕРКОЙ ГОТОВНОСТИ К ВЫПУСКУ, смена #239, на СВЕЖЕЙ установке в пустой проект.

ЧТО ПРОИСХОДИТ. backend_init.py на новой базе штампует meta.schema_version = SCHEMA_VERSION и затем зовёт run_migrations(conn, SCHEMA_VERSION) — то есть применяет только миграции ВЫШЕ текущей версии, а таких нет ни одной. Значит таблицы новой базы берутся ИСКЛЮЧИТЕЛЬНО из CREATE TABLE в backend_schema*.py, а не из миграций.

test_red_history (v60, красная история, закрыта в этой же смене) добавлена ТОЛЬКО миграцией. Замер на свежем проекте: meta.schema_version = 60, таблиц 91, test_red_history НЕТ.

ПОЧЕМУ ЭТО ХУЖЕ ОБЫЧНОГО ДЕФЕКТА. Отказ ТИХИЙ по построению: red_history.record_reds ловит sqlite3.Error и возвращает 0, потому что наблюдение не смеет ронять прогон. То есть у каждого нового проекта красная история пишет в никуда, база при этом честно говорит «схема 60», и ни один гейт не возражает. Это ровно тот класс — механизм есть, работает, и никем не вызывается, — который весь релиз вычищается.

КЛАСС, А НЕ СЛУЧАЙ. Проверять надо не одну таблицу, а свойство: любая таблица, создаваемая миграцией, обязана существовать и на свежей установке. Существующий check_schema_migration_parity сверяет НУМЕРАЦИЮ и этого не видит.

## Acceptance Criteria

AC-1. ЗАМЕР: перечислены ВСЕ таблицы, которые создаются миграциями, и для каждой проверено, есть ли она на свежей установке. Число названо, а не один найденный случай починен.
AC-2. test_red_history создаётся и на свежей установке. Проверяется поднятием пустой базы, а не чтением исходника.
AC-3. НЕГАТИВНЫЙ СЦЕНАРИЙ И ГЛАВНОЕ: тест на СВОЙСТВО — любая таблица, созданная любой миграцией, присутствует на свежей базе. Тест обязан краснеть, если добавить миграцию с новой таблицей и забыть базовую схему. Проверяется подменой, а не рассуждением.
AC-4. Определение таблицы НЕ ДУБЛИРУЕТСЯ двумя расходящимися литералами: миграция по конвенции #646 заморожена навсегда, базовая схема живёт. Способ, которым они держатся вместе, назван в коде.
AC-5. Существующие базы не трогаются: у них таблица уже есть из миграции, и повторное создание идёт через CREATE TABLE IF NOT EXISTS.

## Plan

## Rollback

## Journal

- 2026-09-08T20:23:52Z [implementation] — AC verified: AC-1: ✓ разбор перечисляет ВСЕ таблицы, создаваемые миграциями, и сверяет с настоящей свежей базой. Пропавших было две трактовки: test_red_history (настоящая пропажа) и artifact_edges_v59 с usage_events_v58 (строительные леса перестройки — SQLite не умеет ALTER для CHECK). tests/test_fresh_install_has_every_migrated_table.py::TestСвежаяУстановкаИмеетВсёТоЖе::test_каждая_таблица_миграций_есть_на_свежей_базе AC-2: ✓ проверено ПОДНЯТИЕМ базы, а не чтением исходника: настоящий bootstrap в пустой проект даёт 92 таблицы вместо 91, test_red_history на месте, схема 60. AC-3: ✓ tests/test_fresh_install_has_every_migrated_table.py::TestОхранаУмеетКраснеть::test_выдуманная_таблица_миграции_ловится — подмешивается миграция с таблицей, которой на свежем пути нет, и охрана обязана её увидеть. AC-4: ✓ два определения не расходятся: tests/test_fresh_install_has_every_migrated_table.py::TestСвежаяУстановкаИмеетВсёТоЖе::test_свежий_путь_и_миграция_дают_одинаковую_ФОРМУ сравнивает PRAGMA table_info обеих баз поколоночно. Совпадения ИМЕНИ мало. AC-5: ✓ существующие базы не тронуты: CREATE TABLE IF NOT EXISTS, у них таблица уже есть из миграции. Проверено прогоном миграций на настоящей базе 78 МБ (v57 -> v60, 0.5 с, ноль потерь, integrity ok). Negative: охрана краснеет на подмешанной миграции. ДВА УРОКА ПОЛУЧЕНЫ ИМЕННО ИЗ ПОПЫТКИ ЗАСТАВИТЬ ЕЁ ПОКРАСНЕТЬ, и оба меняли бы вердикт: 1) первая редакция негативного теста взяла номер 9999 и провалилась — run_migrations применяет всё СТРОГО ВЫШЕ штампа, поэтому такая миграция на свежей базе ИСПОЛНЯЕТСЯ и таблица появляется. Тихо пропадают ровно те таблицы, чья миграция НЕ ВЫШЕ SCHEMA_VERSION, то есть каждая уже выпущенная. Номер исправлен на SCHEMA_VERSION - 1. 2) строительные леса именуются здесь суффиксом версии (usage_events_v58, artifact_edges_v59), и без исключения этой формы охрана краснела на двух законных перестройках — её выключили бы первой же. СРАБОТАЛА ЧУЖАЯ ОХРАНА, И ПО ДЕЛУ: test_spec_types_closed_list::test_adr_013_conditional_obligations_are_still_vacuous заметил появление нового класса артефактов и потребовал ответить, не тест-кейс ли это. Не тест-кейс: test_red_history не несёт ни утверждения, ни полярности, ни ссылки на окружение — только наблюдение, что узел, определённый в другом месте, однажды был красным. Ответ записан в scripts/renar_tc_premise.py::CLASSES_AT_DECLARATION с обоснованием, а не молча. Domain: проверено вне тестов дважды. Первый bootstrap в пустой проект: схема 60, 91 таблица, test_red_history НЕТ — дефект воспроизведён. Второй, после починки: схема 60, 92 таблицы, таблица на месте. Плюс цепочка миграций на НАСТОЯЩЕЙ базе 78 МБ с 1560 задачами и 55602 событиями телеметрии: v57 -> v60 за 0.5 с, ноль потерь, integrity_check ok, foreign_key_check 0 нарушений.
