---
slug: gmcp-packaging
title: "[P0] Packaging: build-system + entry-points tausik/tausik-mcp"
status: planning
epic: v2-global-mcp
story: v2gm-packaging
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths:
  - pyproject.toml
  - "scripts/__init__.py"
  - "scripts/project.py"
  - "tests/*"
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

Сделать pyproject реально устанавливаемым: [build-system] (hatchling|setuptools), [project.scripts] -> tausik (CLI) и tausik-mcp (сервер), объявить зависимость mcp. Цель: pipx install / uv tool install даёт на PATH tausik и tausik-mcp, резолвящие проект через find_tausik_dir/resolve_project. scripts/ как пакет.

## Acceptance Criteria

1. Сборка пакета проходит (python -m build / hatch), wheel содержит scripts + mcp + entry-points tausik и tausik-mcp. 2. После установки tausik <cmd> работает из любого каталога TAUSIK-проекта (резолв вверх по дереву). 3. Негативный: запуск tausik вне TAUSIK-проекта -> понятная ошибка с подсказкой tausik init, а не stacktrace. 4. Существующий dev-режим (.tausik/tausik wrapper) не ломается на время перехода. 5. pytest/CI: smoke сборки + entry-points.

## Plan

## Rollback

git revert pyproject-изменений; metadata-only состояние не мешает текущему сабмодулю

## Journal

- 2026-07-18T13:25:20Z [planning] — ПЕРЕЖИВАЕТ ОТМЕНУ 2.0 (решение 2026-07-18). Эпик v2-global-mcp отменён, но эта задача ценна независимо от него и остаётся в работе. Для gmcp-packaging причина прямая: pip-пакет с entry-points делает .mcp.json коммитабельным (ссылка на tausik-mcp в PATH вместо абсолютного пути к интерпретатору), а это предпосылка командной работы из нового эпика shared-knowledge.
