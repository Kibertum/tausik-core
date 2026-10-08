---
slug: svezhaya-shema-migrirovannaya-fikstura-na-kanone-dokazyvaet
title: "Свежая схема ≠ мигрированная: фикстура на каноне доказывает соответствие форме, которой в поле почти нет"
type: gotcha
tags:
  - migrations
  - schema
  - sqlite
  - testing
task: test-ddl-drift-verification-runs
edges: []
---

canonical_ddl() режет DDL из backend_schema.SCHEMA_SQL — это схема БД, созданной С НУЛЯ. У живого проекта БД имеет эту форму РОВНО ОДИН РАЗ, при инициализации; дальше это БД, доведённая миграциями. Если пути расходятся, каждая фикстура на каноне доказывает соответствие форме, которой в поле почти нет.

ОНИ РАСХОДЯТСЯ. Измерено гейтом tests/test_schema_upgrade_parity.py (строит обе БД: свежую из SCHEMA_SQL и мигрированную с v1 через run_migrations, сравнивает PRAGMA table_info по всем 19 таблицам):

1. tasks.model_mismatch — в свежей NOT NULL DEFAULT 0, на пути миграции NULLABLE. На обновлённой БД колонка может быть NULL, и `WHERE model_mismatch = 0` такие строки МОЛЧА ТЕРЯЕТ (в SQLite NULL не равен ничему). Зелено там, где проверяют, неверно там, где работает. Сегодня NULL туда не пишут — это удача, а не защита. Задача schema-model-mismatch-nullable-on-upgrade.

2. ПОРЯДОК КОЛОНОК у tasks и memory. ALTER TABLE ADD COLUMN дописывает в КОНЕЦ, поэтому порядок мигрированной БД неизбежно иной. Не чинится (только перестройкой таблиц), но следствие важнее самого факта: ПОЗИЦИОННЫЙ `INSERT INTO t VALUES (...)` привязан к порядку и потому означает РАЗНОЕ на свежей и обновлённой БД — на CI зелено, у пользователя данные в чужих колонках. Запрещён механически в scripts/ (test_production_code_never_inserts_positionally); в проде нарушений не было, в тестах были и переведены на именованные колонки.

ПРАВИЛО. Добавляя колонку с ограничением, объявляй его ОДИНАКОВО в SCHEMA_SQL и в миграции. Гейт паритета путей теперь ловит расхождение, но только для тех, кто его не обошёл храповиком.

Связано: [[formula-zapisannaya-bolshe-odnogo-raza-razezzhaetsya-v-obe-storony]].
