---
slug: dvoynoy-paritet-shemy-v-testah-fikstura-vs-svezhaya-i
title: "Двойной паритет схемы в тестах: фикстура-vs-свежая И свежая-vs-мигрированная — два разных гейта"
type: pattern
tags:
  - canonical-ddl
  - ddl
  - migration
  - quality-gate
  - schema-parity
  - test-fixtures
task: ddl-parity-narrow-fixtures
edges: []
---

Узкая тест-фикстура, объявляющая таблицу рукописной копией DDL беднее прода, — отдельный КЛАСС молчаливого зелёного: она принимает INSERT, который прод отвергнет по NOT NULL/CHECK, и доказывает соответствие копии, а не продакшену (сессия #119: 20 зелёных тестов при фиче, падавшей IntegrityError в живой БД из-за отсутствия CHECK(scope IN ...)).

В TAUSIK это закрыто ДВУМЯ независимыми гейтами, потому что «схема» — не одна вещь:
1) tests/test_ddl_fixture_parity.py — сверяет КАЖДУЮ фикстуру с backend_schema.SCHEMA_SQL (СВЕЖАЯ схема), параметризован по ВСЕМ таблицам (список выведен из канона, конв. #214). Источник числа колонок — sqlite PRAGMA, не запятые. Исключения — in-place пометка `# ddl-parity: historical — <причина ≥15 симв>`, привязка структурная (ast), fail-closed на неразбираемом файле. НЕ файловый список.
2) tests/test_schema_upgrade_parity.py — сверяет СВЕЖУЮ схему с МИГРИРОВАННОЙ (v1→vN через run_migrations). У живого проекта БД свежая один раз при init; дальше — доведённая миграциями. Ловит: расхождение набора/строгости колонок (напр. tasks.model_mismatch NOT NULL vs nullable — захраповичено, вынесено в задачу-преемника) и order-drift от ALTER TABLE ADD COLUMN (confined {tasks,memory}) → отсюда запрет позиционных INSERT в проде.

ВЫВОД для будущих правок схемы: добавил колонку/таблицу — оба гейта обязаны остаться зелёными; фикстуры бери из conftest.canonical_ddl(table), НИКОГДА не пиши CREATE TABLE руками (кроме миграционных тестов с пометкой historical). Позиционный INSERT INTO t VALUES(...) в проде запрещён — только именованные колонки. См. [[roadmap-hygiene]] контекст релиза 1.8.
