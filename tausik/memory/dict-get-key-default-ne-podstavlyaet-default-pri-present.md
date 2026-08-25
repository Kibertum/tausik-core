---
slug: dict-get-key-default-ne-podstavlyaet-default-pri-present
title: "dict.get(key, default) не подставляет default при present-null"
type: gotcha
tags:
  - config
  - python
  - renar
  - review-finding
task: fix-resolve-assessor-null-config
edges: []
---

При резолве дефолтов из config.json: `cfg.get("k", "")` возвращает None, а НЕ "", если ключ присутствует со значением JSON null. Затем `str(None)` == "None" — фиктивная строка просачивается как валидное значение (поймано ревью в resolve_assessor: assessor='None' в подписываемом RENAR-манифесте). Фикс-паттерн: `str(cfg.get("k") or "").strip()` — `or ""` коллапсит и None, и "". Покрывать тестом ветку present-null отдельно от absent-key. Применимо ко всем config-резолверам.
