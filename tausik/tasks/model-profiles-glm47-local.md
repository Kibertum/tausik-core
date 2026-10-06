---
slug: model-profiles-glm47-local
title: "Профили моделей: glm-4.7 и локальные семейства"
status: planning
epic: kilo-zai-host-parity
story: kilo-zai-foundation
complexity: simple
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
  - provider-agnostic-model-observation
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

Shipped model_profiles заканчиваются glm-4.6, а Kilo+GLM фактически работает на zai-coding-plan/glm-4.7 — рекомендации и under/over-powered verdicts врут. Добавить glm-4.7 в shipped-таблицу (sonnet/opus ранги), зафиксировать шаблон локальных семейств (ollama/*) как данные, проверить калибровку контекстных лимитов; config-override по-прежнему выигрывает.

## Acceptance Criteria

1) task start под Kilo+glm-4.7 даёт корректный verdict и рекомендации из таблицы. 2) Локальная модель из .tausik/config.json резолвится в ранг без правки Python. 3) Негативный: неизвестная модель даёт unknown, а не ложный ранг. 4) Тесты model_profiles обновлены без дублирования (parametrize).

## Plan

## Rollback

## Journal
