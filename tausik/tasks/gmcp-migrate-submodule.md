---
slug: gmcp-migrate-submodule
title: "[P1] Миграция существующих проектов с сабмодуля на глобал"
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
  - "scripts/cli_migrate_global.py"
  - "scripts/project.py"
  - "scripts/project_parser.py"
  - "tests/*"
scope_tools: []
depends_on: []
completed_at: null
resolution: null
resolution_reason: null
tracker_refs:
  - "github#42"
started_model_id: null
started_model_version: null
done_model_id: null
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
---

## Goal

Команда tausik migrate-global: обнаружить проект, установленный сабмодулем (.claude/scripts копия + .gitmodules/сабмодуль), предложить снять per-project копии либы и переключиться на глобальную, сохранив состояние .tausik/ (db/config/keys). Поддержать --dry-run.

## Acceptance Criteria

1. Детект сабмодуль-инсталла (.claude/scripts присутствует И резолвится глобальная либа) -> план миграции. 2. --dry-run печатает что будет удалено/изменено, ничего не трогая. 3. Применение: удаляет per-project копии либы, перерегистрирует MCP на user-scope, .tausik/ остаётся нетронутым (db/keys целы — проверка хэшем). 4. Негативный: проект НЕ сабмодуль-инсталл -> сообщение nothing to migrate, exit 0. 5. Негативный: глобальная либа не установлена -> отказ с подсказкой pipx install, .claude/ не трогаем. 6. pytest: detect, dry-run, apply сохраняет .tausik, не-сабмодуль no-op.

## Plan

## Rollback

git revert команды; миграция идемпотентна и не трогает .tausik/, повторный запуск безопасен; для проекта — восстановить .claude из git

## Journal
