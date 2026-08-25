---
slug: verify-task-skipaet-scoped-geyty-pytest-poka-relevant-files
title: "verify --task скипает scoped-гейты (pytest), пока relevant_files не персистнуты через task update --relevant-files"
type: gotcha
tags:
  - dogfooding
  - qg2
  - verify-first
  - workflow
task: memory-pretool-block-skip-toggle-and-docstring
edges: []
---

Порядок закрытия QG-2 при существующей НЕзакоммиченной куче в дереве:

1. `tausik verify --task <slug>` скоупит pytest к ПЕРСИСТНУТОЙ колонке relevant_files. Если она пуста — pytest выдаёт [SKIP] (не запускается!), verify-run записывается без pytest, и `task done` падает verify-first «no fresh verify run (gates: hadolint, pytest)». Текст поля `scope` НЕ populate'ит relevant_files.
2. Фикс: сперва `tausik task update <slug> --relevant-files A B` (CLI принимает флаг, хотя MCP task_update его в схеме НЕ показывает), ПОТОМ verify (pytest реально прогонится), ПОТОМ `task done --ac-verified`.
3. Передача --relevant-files только в `task done` регистрирует их поздно и не помогает verify отскоупиться заранее.
4. При pre-existing куче (напр. накопление к релизу) verify пишет NOTE «N files changed since task start but not declared» — это информационно, НЕ блок. Но MCP-путь task_done в этом состоянии даёт cache_status=git-mismatch и не закрывает — падать на CLI (перечитывает диск каждый вызов).

Симптом-триггер: verify PASS, а task done всё равно требует verify заново → проверь, что pytest в выводе verify был PASS, а не SKIP.
