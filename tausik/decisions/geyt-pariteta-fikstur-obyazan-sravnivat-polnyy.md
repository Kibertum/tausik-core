---
slug: geyt-pariteta-fikstur-obyazan-sravnivat-polnyy
task: schema-model-mismatch-nullable-on-upgrade
date: "2026-07-27"
edges: []
---

## Decision

Гейт паритета фикстур обязан сравнивать ПОЛНЫЙ нормализованный DDL, а не только PRAGMA table_info: последний слеп к CHECK/FK/UNIQUE, которые живут лишь в тексте CREATE.

## Rationale

L3-ревью v43 нашло дыру: перестройка центральной таблицы по рукописному frozen-снимку DDL проходила бы гейт колонок даже при дрейфе CHECK/FK/UNIQUE между снимком и SCHEMA_SQL. Закрыто test_rebuilt_tasks_ddl_matches_including_constraints: нормализация + прямое сравнение fresh vs migrated sqlite_master.sql. Правило общее: проверка эквивалентности схем на table_info недоопределена по ограничениям.
