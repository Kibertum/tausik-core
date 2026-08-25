---
slug: v156-dedup-normalize-model-id
title: "v156 DRY: дедуп normalize_model_id (model_profiles vs model_routing_matrix)"
status: done
epic: null
story: null
complexity: simple
role: developer
stack: null
tier: null
call_budget: null
defect_of: null
scope: "scripts/model_routing_matrix.py (убрать дубль), при необходимости model_profiles.py."
scope_exclude: "Не менять публичный API/сигнатуры; model_routing.py re-export не трогать."
relevant_files:
  - "scripts/model_routing_matrix.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-19T11:51:53Z"
---

## Goal

Устранить дублирование normalize_model_id между scripts/model_profiles.py и scripts/model_routing_matrix.py — вынести в общий хелпер. Отложено с v1.5.5.

## Acceptance Criteria

1. Единственная реализация normalize_model_id в model_profiles.py; model_routing_matrix.py использует её (алиас _normalize_model_id = model_profiles.normalize_model_id), дублирующий _BRACKET_SUFFIX в matrix удалён. 2. Поведение идентично (lowercase + strip trailing [Nm]); re-export _normalize_model_id из model_routing.py продолжает работать. 3. pytest зелёный (test_model_profiles, test_model_routing). 4. Ошибка/abort (негатив): если хоть один импорт _normalize_model_id ломается или меняется поведение нормализации (напр. на входе 'Opus 4.8[1m]') — откатить, не закрывать.

## Plan

## Rollback

git checkout scripts/model_routing_matrix.py.

## Journal

- 2026-06-19T11:51:52Z [implementation] — AC verified: 1.✓ единственная impl в model_profiles.normalize_model_id; matrix._normalize_model_id = алиас, дублирующий _BRACKET_SUFFIX + неиспользуемый import re удалены. 2.✓ поведение идентично (smoke: 'Opus 4.8[1m]'→'opus 4.8', None→'', family opus); re-export model_routing._normalize_model_id is model_profiles.normalize_model_id == True. 3.✓ ruff All checks passed; pytest test_model_profiles+test_model_routing 44 passed; full verify green. 4.✓ negative: импорты/поведение не сломались (smoke + tests). Domain: нормализация id остаётся корректной на реальных входах (версии моделей с [1m] суффиксом).
