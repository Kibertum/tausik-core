---
slug: model-profiles-glm47-local
title: "Профили моделей: glm-4.7 и локальные семейства"
status: done
epic: kilo-zai-host-parity
story: kilo-zai-foundation
complexity: simple
role: developer
stack: null
tier: null
call_budget: null
defect_of: null
scope: "scripts/model_profiles.py shipped defaults (glm-4.7 sonnet/opus/fable, ollama local family as data) + vendor tokens if needed; tests/test_model_profiles.py parametrized; docs en/ru kilo-zai section 5; CHANGELOG en/ru"
scope_exclude: null
relevant_files:
  - "scripts/model_profiles.py"
  - "tests/test_model_profiles.py"
  - "tests/test_model_routing.py"
  - "tests/test_task_start_model_banner.py"
  - "docs/en/kilo-zai.md"
  - "docs/ru/kilo-zai.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths: []
scope_tools: []
assurance_profiles: []
assurance_impact: null
depends_on:
  - provider-agnostic-model-observation
completed_at: "2026-10-06T19:01:08Z"
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

- 2026-10-06T18:44:09Z [implementation] — CHECKPOINT: glm-4.7 в DEFAULT_FAMILIES (sonnet/opus/fable) + normalize_model_id снимает provider-префикс и [Nk]-суффикс; дамп-оракул зелёный: 5 написаний glm-4.7 to fable, glm-4.6 выпал to None, ollama из конфига резолвится. test_model_profiles.py: 16 passed. test_model_routing.py: collection error после скрипт-патча (имя переменной в блоке _model_tier). test_task_start_model_banner.py: 3 failed, pytest видит старые glm-4.6 при 4/4 заменах — проверить диск программно. Темп-оракулы: dump_profiles.py, patch_tests_glm47.py в TEMP\kilo. Осталось: 2 теста, docs en/ru секц.5, CHANGELOG, verify, done, push.
- 2026-10-06T18:58:45Z [implementation] — test_model_routing.py collection error fixed (lines 302-303 lost indentation; names verified by codepoint dump); banner tests re-pointed glm-4.6->glm-4.7 (3 spots); 113 passed across banner+routing+profiles. Docs en/ru kilo-zai.md: KILO_MODEL example, table, diagram -> glm-4.7; local ollama family example + prefix/[Nk] calibration paragraph added. CHANGELOG en/ru: Fixed section 'model verdicts lied on GLM-4.7' (stale table, matcher calibration, test matrix).
- 2026-10-06T19:00:56Z [implementation] — AC verified: 1. check — banner tests: glm-4.7 active on complex -> recommendation glm-4.7 + model match (test_glm_active_recommends_glm_and_matches); under/over verdicts covered by routing+banner suites, 113 passed (verify #3532: 1297 passed). 2. check — oracle dump: ollama2/glm-4.5-air resolves to haiku rank from clean config, no Python change; config entry ollama/glm-4.5-air:latest -> haiku (override wins). 3. check — negative: glm-4.6 (dropped) -> None, unknown-model -> None; asserted in test_model_tier_resolves_glm_via_profiles and parametrized profile tests. 4. check — tests/test_model_profiles.py parametrized over spelling matrix; audit_pytest_dedupe gate green in verify #3532.
