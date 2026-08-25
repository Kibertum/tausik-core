---
slug: protechka-zadach-kai-raven-v-roadmap-tausik-signatura
title: "Протечка задач kai/raven в roadmap TAUSIK: сигнатура фантома и как отсеивать"
type: gotcha
tags:
  - adapt
  - kai-raven-leak
  - phantom-task
  - release-1.8
  - roadmap-hygiene
task: null
edges: []
---

В эпике landscape-2026-h2 (релиз 1.8) обнаружены и удалены ДВЕ задачи-фантома, автозаведённые из L3-ревью ЧУЖОГО фреймворка kai/raven (сессия #88), а не TAUSIK: `fork-new-version-writes-content-not-adapt-body` и `freeze-tests-double-fidelity-and-source-text-assert`.

СИГНАТУРА ФАНТОМА (любой из признаков = проверяй существование кода перед стартом):
- ссылки на `fork_new_version`, `service_renar_lifecycle.py`, `service_renar_adapt.py`, `agents/*/mcp/raven/server.py` — их нет в TAUSIK;
- поля документа `content` / `rationale` / `alternatives_considered`, `content_hash`, generic `semver bump`/`supersedes` — НЕ модель ADAPT в TAUSIK;
- премиса про **CouchDB `_rev`-конфликты** (`_Couch`, `couch_get`, AsyncMock-прокси) — TAUSIK на **SQLite**;
- символы с префиксом `kai_*`, имена `raven`/`kai` В КОДЕ (в CHANGELOG/доках — норм, это история).

РЕАЛЬНАЯ модель ADAPT в TAUSIK (backend_schema_adapts.py): таблица `adapts` с tz_ref/status(draft|signed|superseded)/parent_adapt/delta_n; версионирование через parent_adapt+delta_n+superseded, БЕЗ fork_new_version и без поля content.

КАК ОТСЕИВАТЬ: перед `task start` на незнакомой l26-задаче извлеки из goal конкретные файловые/символьные ссылки и проверь Glob/Grep. Если ПЕРВИЧНЫЕ файлы/функции отсутствуют во всём дереве — это фантом, НЕ реализуй, удаляй из roadmap (переносить некуда — проекта kai/raven у нас нет). Осторожно: задача, создающая НОВЫЙ артефакт (напр. memory_route_gate), законно ссылается на несуществующее — это by design, не фантом.

Скан оставшихся 21 planning-задач 1.8 (сессия #127) подтвердил: больше фантомов нет.
