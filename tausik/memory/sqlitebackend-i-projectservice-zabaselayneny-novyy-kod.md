---
slug: sqlitebackend-i-projectservice-zabaselayneny-novyy-kod
title: "SQLiteBackend и ProjectService забаселайнены: новый код кладётся модульной функцией, а не публичным методом"
type: convention
tags:
  - architecture
  - class-surface
  - gates
task: usage-attribution-is-keyed-by-task-not-session
edges: []
---

tausik/gates.json.class_surface.baseline = {SQLiteBackend: 129, ProjectService: 118}, и храповик test_gate_class_surface требует РАВЕНСТВА, а не «не больше»: баселайн обязан совпадать с реальностью и может только сокращаться. Значит ЛЮБОЙ новый публичный метод на этих двух классах красит гейт — не «когда-нибудь перерастём», а на первом же добавлении.
ЗАМЕР #192: добавление usage_events_unattributed_rollup в миксин backend_queries_usage дало «SQLiteBackend grew: 130 > baseline 129». Второе такое же нарушение (ProjectService 118 -> 119) пряталось за ним и вылезло бы следующим — цикл assert падает на первом ключе словаря.
РЕШЕНИЕ: класть модульной функцией в том же модуле, где живёт слой (SQL остаётся в backend_queries_usage, нормализация границ окна — в project_service, а метод-делегат сохраняет прежних вызывающих). Функции без состояния экземпляра это и есть их настоящая форма.
ЧЕГО НЕ ДЕЛАТЬ: переименовывать в _приватное ради счёта. Гейт считает публичные члены, так что сработает — и будет обходом правила, а не его соблюдением: поверхность накапливается всё равно, а вызывающий из другого модуля лезет в чужое приватное.
