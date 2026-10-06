---
slug: kilo-gate-plugin
title: "Kilo gate plugin: Rule 1/2/10.12 через tool.execute.before"
status: planning
epic: kilo-zai-host-parity
story: kilo-zai-foundation
complexity: complex
role: developer
stack: null
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
assurance_profiles: []
assurance_impact: null
depends_on:
  - kilo-mcp-live-wiring
completed_at: null
resolution: null
resolution_reason: null
tracker_refs: []
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

Enforcement coverage на Kilo сейчас kilo:none. Использовать подтверждённый plugin API Kilo (.kilo/plugins/*.{js,ts} автозагрузка + plugin в конфиге; Hooks: tool.execute.before, permission.ask): плагин tausik-gates перед edit/write/bash вызывает переиспользуемые task_gate.py/scope-гейты и отклоняет вызов без активной задачи; секрет-скан аргументов bash. Плюс дешёвый слой: permission {edit,bash}:ask в генерируемом kilo.jsonc. Обязателен живой замер по образцу Codex-истории: недоверенный/выключенный профиль ничего не исполняет — заявляем только измеренное.

## Acceptance Criteria

1) Живой замер: без активной задачи forbidden write через edit и через bash отклонён ДО мутации; файл не создан; отказ виден агенту как ошибка вызова. 2) С активной задачей те же операции проходят. 3) Задокументировано измеренно: выключенный плагин = нулевое исполнение (по примеру codex trust-precondition). 4) Генератор ставит плагин и permission-профиль; тест удерживает deployment; enforcement coverage показывает kilo как covered по Rule 1/2. 5) Негативный: task_done без verify-cache по-прежнему блокируется (QG-2 не ослаблен).

## Plan

## Rollback

## Journal
