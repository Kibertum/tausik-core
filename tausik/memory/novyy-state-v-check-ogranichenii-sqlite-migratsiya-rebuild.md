---
slug: novyy-state-v-check-ogranichenii-sqlite-migratsiya-rebuild
title: "Новый state в CHECK-ограничении SQLite = миграция-rebuild таблицы"
type: gotcha
tags:
  - ddl
  - fix
  - migration
  - sqlite
  - verify
task: null
edges: []
---

SQLite не умеет ALTER CHECK-констрейнт: расширение домена состояния (например 'invalidated' для verification_cohorts.state) требует миграцию-rebuild — CREATE TABLE new / INSERT INTO new SELECT / DROP old / RENAME, и синхронной правки CREATE TABLE в backend_schema.py. DDL-parity пины сравнивают миграции со схемой, так что рассинхрон ловится гейтом, но ошибка проявляется как IntegrityError в рантайме (verify_cohort _set_state), а не при создании.
