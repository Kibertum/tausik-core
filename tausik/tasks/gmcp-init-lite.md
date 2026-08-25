---
slug: gmcp-init-lite
title: "[P1] tausik init: только .tausik/ + user-scope MCP регистрация"
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
  - "scripts/cli_init.py"
  - "scripts/project.py"
  - "scripts/project_parser.py"
  - "tests/*"
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

Лёгкий tausik init для глобальной модели: в проекте создаёт ТОЛЬКО .tausik/ (db через миграции + config + keys), без копирования .claude/scripts|mcp. Регистрирует user-scope MCP (claude mcp add --scope user tausik-project ИЛИ печатает готовый сниппет для ~/.claude.json). Заменяет тяжёлый bootstrap-copy.

## Acceptance Criteria

1. tausik init в пустом проекте создаёт .tausik/{tausik.db,config.json} и НЕ создаёт .claude/scripts|mcp копий. 2. Печатает/применяет user-scope MCP регистрацию (идемпотентно: повтор не дублирует). 3. Негативный: init в уже инициализированном проекте -> no-op с сообщением, без перезатирания db/keys. 4. Негативный: нет прав/недоступен ~/.claude.json -> печатает сниппет вручную, exit без краша. 5. pytest: свежий init, повторный init, режим печати сниппета.

## Plan

## Rollback

git revert; старый bootstrap.py остаётся доступным как dev-путь

## Journal

- 2026-07-18T13:25:20Z [planning] — ПЕРЕЖИВАЕТ ОТМЕНУ 2.0 (решение 2026-07-18). Эпик v2-global-mcp отменён, но эта задача ценна независимо от него и остаётся в работе. Для gmcp-packaging причина прямая: pip-пакет с entry-points делает .mcp.json коммитабельным (ссылка на tausik-mcp в PATH вместо абсолютного пути к интерпретатору), а это предпосылка командной работы из нового эпика shared-knowledge.
