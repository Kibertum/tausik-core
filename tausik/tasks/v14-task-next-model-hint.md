---
slug: v14-task-next-model-hint
title: "(Опционально) подсказка модели в task_next / HUD"
status: done
epic: v14-model-prompts
story: v14-model-prompts-autosuggest
complexity: medium
role: null
stack: null
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/service_task_team.py"
  - "scripts/project_config.py"
  - "docs/en/cli.md"
  - "docs/ru/cli.md"
  - "tests/test_task_next_model_hint.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-01T15:43:35Z"
---

## Goal

Feature-flag; рекомендация без блокировки старта задачи.

## Acceptance Criteria

1. За флагом конфига. 2. Документация. 3. Negative: при выключенном флаге поведение как сейчас без ошибок.

## Plan

## Rollback

## Journal

- 2026-05-01T15:42:51Z [implementation] — AC: 1. Флаг в config (task_next.model_hint) — is_task_next_model_hint_enabled. 2. Документация docs/en/cli.md и docs/ru/cli.md. 3. Тесты tests/test_task_next_model_hint.py (7 passed). MCP handlers синхронизированы (cursor, qwen). verify --task: pytest PASS.
- 2026-05-01T15:42:59Z [implementation] — AC verified: 1. Конфиг task_next.model_hint и is_task_next_model_hint_enabled — ✓ 2. Документация EN/RU cli — ✓ 3. Выключенный флаг / без ключа — без model_hint, ошибок нет — ✓ (тесты + verify pytest).
