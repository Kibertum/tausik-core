---
slug: okno-sobytiy-po-vremeni-now-granitsa-sekundnyy-timestamp
title: "Окно событий по времени: 'now'-граница + секундный timestamp = флейк"
type: gotcha
tags: []
task: null
edges: []
---

utcnow_iso()='%Y-%m-%dT%H:%M:%SZ' СЕКУНДНОЙ гранулярности. Любой запрос, ограничивающий окно сверху julianday('now') И сравнивающий со свежезаписанными событиями, флейкует: 'now' при чтении может оказаться РАНЬШЕ created_at только что записанного события (усечение к следующей секунде / skew писатель-vs-SQLite'now'), событие выпадает. Проявилось как task_event_count_in_window undercount (windows-3.13, assert 3>=4, 1/11 ячеек CI; локально не воспроизводится). Фикс: для ОТКРЫТОГО интервала (активная задача, completed_at NULL) не ставить верхнюю границу вообще — она бессмысленна; cap применять только к закрытому интервалу (completed_at). Тестировать детерминированно: вставлять событие с контролируемым created_at через be._ins (event_add жёстко ставит utcnow). Связано с [[event-window-boundary-flake]].
