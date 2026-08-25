---
slug: v14-bootstrap-model-env
title: "Генерация TAUSIK_MODEL_PROFILE в config (опционально)"
status: done
epic: v14-model-prompts
story: v14-model-prompts-routing
complexity: medium
role: null
stack: null
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "tests/test_bootstrap_model_profile.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-01T13:59:01Z"
---

## Goal

Bootstrap записывает профиль модели если задан в окружении.

## Acceptance Criteria

1. Ключ в .tausik/config.json документирован. 2. Bootstrap --refresh безопасен. 3. Negative: невалидное значение профиля отвергается.

## Plan

## Rollback

## Journal

- 2026-05-01T13:58:56Z [implementation] — AC verified: 1. ✓ quickstart EN/RU + mcp.md 2. ✓ bootstrap --refresh 3. ✓ tests test_bootstrap_model_profile invalid env exit non-zero; TAUSIK_MODEL_PROFILE=claude writes model_profile; pytest tests/test_bootstrap_model_profile.py
