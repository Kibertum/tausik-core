---
slug: v15-risk-model
title: "[P1] Композитная risk-модель на закрытие задачи"
status: done
epic: v15-evidence-attestation
story: v15-risk-score
complexity: complex
role: architect
stack: python
tier: null
call_budget: null
defect_of: null
scope: "risk_model.py (pure stdlib, без I/O) + docs/ru/research/risk-model.md + тесты"
scope_exclude: "service_gates.py/service_task.py (интеграция = отдельная задача v15-risk-compute-on-done)"
relevant_files:
  - "scripts/risk_model.py"
  - "tests/test_risk_model.py"
scope_paths:
  - "scripts/risk_model.py"
  - "docs/ru/research/risk-model.md"
  - "tests/*"
scope_tools: []
depends_on: []
completed_at: "2026-06-12T01:28:13Z"
---

## Goal

Спроектировать композитный risk-score 0.0-1.0 для закрытия задачи из факторов: покрытие гейтов, дельта тестов, полнота AC-evidence, code churn, security-pattern хиты. Веса, формула, обоснование. Документ + интерфейс расчёта.

## Acceptance Criteria

1. risk_model.compute_risk(factors) -> {score 0.0-1.0, level low/medium/high, factors, weights}; детерминированный, stdlib-only, веса нормированы (сумма=1). 2. Нормализаторы 5 факторов: gate_coverage, test_delta, ac_evidence, code_churn, security_hits — каждый клампится в [0,1]. 3. Негативный: неизвестный фактор/значение вне [0,1]/NaN -> ошибка ValueError (не тихий мусор); отсутствующий фактор -> консервативный дефолт 1.0 (риск) с пометкой в выводе. 4. Документ docs/ru/research/risk-model.md: формула, веса, обоснование каждого веса, пороги уровней, известные ограничения. 5. pytest: формула/веса/клампы/негативы/монотонность (рост фактора не снижает score).

## Plan

## Rollback

git revert: чистый новый модуль risk_model.py + research-документ, ни один существующий флоу не вызывает его до v15-risk-compute-on-done; откат не затрагивает данные

## Journal

- 2026-06-12T01:28:12Z [implementation] — AC verified: 1-5 OK, см. лог выше (23 теста, decision #92, research-док).
- 2026-06-12T01:28:12Z [implementation] — AC-1: ✓ tests/test_risk_model.py::TestComputeRisk (weighted sum, weights=1.0, levels); AC-2: ✓ TestNormalizers (5 нормализаторов, клампы); AC-3 Negative: ✓ test_invalid_input_raises (unknown/range/NaN/Inf/str) + test_missing_factor_defaults_to_risky_and_reported; AC-4: ✓ docs/ru/research/risk-model.md (формула/веса/обоснования/пороги/5 ограничений); AC-5: ✓ test_monotonic_in_every_factor, 23 passed
