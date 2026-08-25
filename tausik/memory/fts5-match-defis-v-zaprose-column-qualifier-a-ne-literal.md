---
slug: fts5-match-defis-v-zaprose-column-qualifier-a-ne-literal
title: "FTS5 MATCH: дефис в запросе — column-qualifier, а не литерал"
type: gotcha
tags:
  - fts5
  - python
  - sqlite
  - testing
task: brain-local-schema
edges: []
---

В SQLite FTS5 строка вида `Unique-marker-42` в `MATCH ?` парсится как `Unique` + column-qualifier `marker:42` и падает с `no such column: marker`. Чтобы искать литеральные слова с дефисами — либо обрамляй запрос в двойные кавычки (`"Unique-marker-42"`), либо используй маркеры без дефисов в тестах. Проявилось в test_brain_schema.py при первом прогоне; фикс — переименовать marker → UniqueMarker42.
