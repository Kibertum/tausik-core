---
slug: notion-client-inektsiya-urlopen-clock-sleep-cherez
task: brain-notion-rest-client
date: "2026-04-23"
edges: []
---

## Decision

Notion client: инъекция (urlopen, clock, sleep) через конструктор вместо monkeypatch в тестах

## Rationale

Все 26 unit-тестов без сетевого I/O и без monkeypatch глобальных модулей. Инъекция держит class testable, retry/throttle детерминированно проверяются через _ClockSleep recorder. Продакшн-умолчания (urllib.request.urlopen, time.monotonic, time.sleep) собираются внутри __init__.
