---
slug: bag-obnovleniya-1-8-1-9-vladelets-konsumer-14-09-2026-init
title: "Баг обновления 1.8→1.9 (владелец, консумер, 14.09.2026): init_schema создаёт actz_points с tz_ref до миграций, v53 падает на duplicate column, версия остаётся 44"
type: context
tags:
  - bug
  - consumer
  - migration
  - release-1.9
  - upgrade
task: upgrade-from-1-8-crashes-at-v53-and-leaves-the-version-at-44
edges: []
---

Механизм подтверждён по исходнику backend_init.init_schema: на существующей базе все кумулятивные схемные скрипты (в т.ч. ACTZ_SQL с CREATE TABLE IF NOT EXISTS actz_points … tz_ref) выполняются ДО run_migrations; на базе v44 таблицы нет — создаётся в текущей форме; затем v53 ALTER TABLE … ADD COLUMN tz_ref → duplicate column. run_migrations коммитит каждую миграцию, а schema_version пишет init_schema после всей цепочки → v45–v52 закоммичены, штамп 44, повторный старт падает на v47. Тесты миграций зовут run_migrations напрямую без кумулятивных скриптов — путь потребителя (init_schema на v44) не гонялся. Владелец починил у себя вручную (толерантность к duplicate column, бэкапы). Заведено: задача upgrade-from-1-8-crashes-at-v53-and-leaves-the-version-at-44 (1.10 B, complex), issue github#51; рекомендация — 1.9.1, потому что README ведёт каждого пользователя 1.8 в падение.
