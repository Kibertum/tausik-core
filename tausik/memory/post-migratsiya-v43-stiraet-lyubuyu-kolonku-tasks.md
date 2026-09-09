---
slug: post-migratsiya-v43-stiraet-lyubuyu-kolonku-tasks
title: "Пост-миграция v43 стирает любую колонку tasks, добавленную после v43"
type: gotcha
tags: []
task: post-migration-v43-erases-every-column-added-after-it
edges: []
---

maybe_rebuild_tasks_v43 зовётся из run_post_migrations ПОСЛЕ версионной петли run_migrations и пересобирает tasks по ЗАМОРОЖЕННЫМ _CREATE_TASKS_NEW/_TASKS_COLUMNS эпохи v43: копирование идёт по явному списку имён, DROP TABLE tasks уносит остальное. На цепочке с v1 run_migrations возвращает 61, а колонки из миграции v61 в таблице НЕТ — при том что на свежем пути она есть. Живые базы не задеты: _needs_rebuild даёт 0, когда model_mismatch уже NOT NULL. Ловит это только test_schema_upgrade_parity, и он покраснел на первой колонке, добавленной после v43 за всё время. Прежде чем добавлять колонку в tasks — прогони этот тест.
