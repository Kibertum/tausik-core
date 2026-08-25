---
slug: v15mr-fable-tier-fix
title: "[P0] Tier-aware mismatch: fable в реестре, сравнение по тирам"
status: done
epic: v15-model-routing
story: v15mr-phase-routing
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/model_routing.py — добавить _TIER_ORDER + _model_family/_model_tier, переписать вердикт format_task_start_banner на сравнение тиров, fable в _PROFILE_SLUG_BY_MODEL_ID. tests/test_task_start_model_banner.py — переписать mismatch-тест под новую семантику + новые тесты."
scope_exclude: "_ROUTING/suggest_model контракт (id моделей claude-opus-4-7 и т.п. НЕ менять — на них завязаны regression-тесты), service_task.py, project_config.py"
relevant_files:
  - "scripts/model_routing.py"
scope_paths:
  - "scripts/model_routing.py"
  - "scripts/model_routing_session.py"
  - "tests/*"
scope_tools: []
depends_on: []
completed_at: "2026-06-13T09:18:36Z"
---

## Goal

claude-fable-5 в реестре моделей (tier над opus); вердикт mismatch по ПОРЯДКУ тиров, а не равенству: active >= recommended -> OK/info (запас качества + подсказка экономии), active < recommended -> warning. Убрать ложные MODEL MISMATCH на каждом task start под fable (наблюдалось всю сессию 79).

## Acceptance Criteria

1. fable известен реестру: tier-порядок haiku<sonnet<opus<fable, fable в _PROFILE_SLUG_BY_MODEL_ID; banner при active=fable и recommended sonnet/haiku/opus -> info про экономию (switch down), НЕ warning. 2. Ошибка/boundary: active тир НИЖЕ recommended (haiku при complex) -> warning MODEL MISMATCH сохраняется. 3. Ошибка/boundary: неизвестный model id -> без исключения, вердикт info-класса (active model unrecognized). 4. pytest: tier-ordering + все ветки format_model_banner зелёные.

## Plan

## Rollback

git revert коммита; вердикт возвращается к сравнению по равенству. Конфиг/БД не затрагиваются.

## Journal

- 2026-06-13T09:18:25Z [implementation] — Tier-aware вердикт: _model_family/_model_tier (haiku<sonnet<opus<fable, по семейству а не версии). active>=rec -> info quality-surplus (switch down), active<rec -> warning MODEL MISMATCH, unknown id -> info. fable+opus-4-8 в slug-карте. Ложный MISMATCH (opus-4-8 vs sonnet) устранён. 38 тестов зелёные.
- 2026-06-13T09:18:36Z [implementation] — AC verified: 1. ✓ fable surplus->info (test_fable_active_against_sonnet_is_surplus, test_surplus_is_info_not_warning). 2. ✓ под-мощность warning (test_under_powered_is_loud_warning). 3. ✓ unknown id info (test_unrecognized_active_is_info). 4. ✓ tier-ordering (TestTierOrdering) + opus-4-8 match (test_opus_point_release_matches_complex). pytest 38 passed.
