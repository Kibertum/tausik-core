---
slug: zamer-192-tret-zhurnala-rashoda-ne-popadala-ni-v-odin-otchet
title: "Замер #192: треть журнала расхода не попадала ни в один отчёт"
type: context
tags:
  - measurement
  - telemetry
  - usage-events
task: usage-attribution-is-keyed-by-task-not-session
edges: []
---

На живой .tausik/tausik.db сразу после миграции v48: 56413 строк usage_events, из них 18638 — с NULL task_slug и не зеркальные (source <> 'session_record'). Это ТРЕТЬ журнала, которая до сегодня не была видна нигде: ролап по задачам отбирает `task_slug IS NOT NULL` (правильно — иначе удвоение), а дополнения к нему не печатал никто.
Хвоста «вне сессии» у корзины НОЛЬ, и это верно, а не подозрительно: до v48 схема запрещала session_id=NULL, а хук дропал событие без открытой сессии, так что дов48-строки все писались внутри сессий, но вне задач.
Проверено там же: schema_version=48, session_id notnull=0, оба FK = ON DELETE SET NULL, 56413 строк на месте после перестройки.
Цифра нужна как отправная точка: после v48 в корзину начнёт попадать и работа без сессии, и рост этого числа будет означать РАЗНОЕ — либо больше работы вне задач, либо агент забывает task start. Различать их позволяет отдельный счёт sessionless_events.
