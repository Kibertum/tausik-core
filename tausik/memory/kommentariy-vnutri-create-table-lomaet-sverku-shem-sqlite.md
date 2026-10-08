---
slug: kommentariy-vnutri-create-table-lomaet-sverku-shem-sqlite
title: "Комментарий ВНУТРИ CREATE TABLE ломает сверку схем: sqlite хранит текст оператора дословно, вместе с комментариями"
type: gotcha
tags:
  - migrations
  - schema
  - sqlite
  - tests
task: senar-14-gates-declare-the-effect-they-prevent
edges: []
---

Добавил колонку в backend_schema_gate_runs.py и объяснил её комментарием `-- ...` прямо в теле CREATE TABLE. Свежая схема перестала совпадать с мигрированной: test_gate_runs_persist::test_migrated_and_fresh_schemas_are_identical сравнивает нормализованный текст из sqlite_master, а ALTER TABLE никаких комментариев не добавляет. Комментарий надо ставить ВЫШЕ присваивания с DDL (обычным python-комментарием), а не внутри оператора. Там же второе: тест вида `assert SCHEMA_VERSION == _V50` в модуле про миграцию v50 краснеет при КАЖДОЙ следующей миграции — «зарегистрирована и достигнута» (>=) есть то, что остаётся верным, а «== текущая» верно ровно одну версию.
