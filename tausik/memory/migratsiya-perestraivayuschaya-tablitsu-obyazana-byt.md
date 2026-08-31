---
slug: migratsiya-perestraivayuschaya-tablitsu-obyazana-byt
title: "Миграция, перестраивающая таблицу, обязана быть охраняемым пост-шагом, а не списком SQL"
type: convention
tags:
  - fixtures
  - migrations
  - schema
  - sqlite
task: usage-attribution-is-keyed-by-task-not-session
edges: []
---

Список утверждений не умеет пропустить сам себя. Тесты миграций поднимают МИНИМАЛЬНУЮ БД и гонят run_migrations с версии 32/36/..., чтобы проверить ОДНУ миграцию; таблица, созданная миграцией НИЖЕ стартовой версии, там не существует. Слепой `DROP TABLE t` / `INSERT ... FROM t` в конце цепочки роняет весь такой прогон.
ЗАМЕР #192: v48 в форме списка (дословно по образцу v24 на той же таблице) уронила test_adapts.py::test_migration_v36_creates_tables_clean и test_reasoning_steps.py::test_migration_v32_creates_table_triggers_clean — обе `no such table: usage_events`. v24 этого не встречала: таких фикстур в её время не было, то есть образец устарел молча.
ФОРМА: MIGRATION_VNN = [] как маркер версии для check_schema_migration_parity, плюс maybe_<действие>_vNN(conn) в backend_migrations_postseed.run_post_migrations под `if current_version >= NN`. Приём уже был у v42_backfill и v43.
ОХРАНА пишется как «ровно то состояние, которое чинится» (таблица есть И колонка ещё NOT NULL) — из этого бесплатно следует идемпотентность и пропуск на свежей БД.
Урок закрепляй ОТДЕЛЬНЫМ тестом охраны, а не полагайся на те два: они проверяют СВОИ миграции и завтра переедут на другую стартовую версию, унеся покрытие чужого дефекта.
