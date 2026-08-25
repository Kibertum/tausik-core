---
slug: v15-l3-risk-trigger
title: "[P2] High-risk → обязательный L3 adversarial review"
status: done
epic: v15-evidence-attestation
story: v15-selective-l3
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "risk_l3_trigger.py + вызов в service_task_done"
scope_exclude: "risk_model.py/risk_compute.py (заморожены)"
relevant_files:
  - "scripts/risk_l3_trigger.py"
  - "scripts/service_task_done.py"
  - "tests/test_risk_l3_trigger.py"
scope_paths:
  - "scripts/risk_l3_trigger.py"
  - "scripts/service_task_done.py"
  - "tests/*"
scope_tools: []
depends_on: []
completed_at: "2026-06-12T01:58:55Z"
---

## Goal

Закрытия с risk-score выше порога триггерят обязательный L3 adversarial review (пометка review-required / блок до review). Селективная эскалация ~1% критичных вместо единой политики. Заимствует HITL-for-1% Walko.

## Acceptance Criteria

1. Негативный: закрытие с measured-high risk (renormalized score по измеренным факторам >= 0.66 ПРИ покрытии измеренными факторами >= 0.75 весов модели) без записанного L3-ревью -> blocking failure stage=risk, задача НЕ закрыта, remediation в сообщении. 2. Записанный L3 для задачи (run_type L3, case-insensitive) -> закрытие проходит, note об эскалации. 3. High из-за defaulted-факторов ИЛИ при покрытии < 0.75 (включая casual-паттерн test_delta+ac_evidence) -> НЕ блокирует; low/medium -> не блокирует. 4. Негативный: config risk.l3_block_on_high=false -> warning вместо блока. 5. pytest: блок/пропуск-с-ревью/defaulted-high/coverage-порог/opt-out + интеграционный done-цикл.

## Plan

## Rollback

git revert; мгновенный opt-out: config risk.l3_block_on_high=false; триггер срабатывает только на measured-high (renormalized по измеренным факторам), так что legacy-проекты без verify-гейтов не блокируются

## Journal

- 2026-06-12T01:58:54Z [implementation] — AC verified: 1-5 OK см. лог (decision #93, full suite 3522 green).
- 2026-06-12T01:58:54Z [implementation] — AC-1 Negative: ✓ tests/test_risk_l3_trigger.py::TestCheckL3Required::test_measured_high_without_review_blocks + TestTaskDoneIntegration (status active после блока); AC-2: ✓ test_recorded_l3_satisfies + test_run_type_case_insensitive; AC-3: ✓ test_defaulted_only_high_does_not_block + test_thin_measurement_coverage + test_casual_close_pattern (live boundary-флейк 0.6667 закреплён тестом); AC-4 Negative: ✓ test_opt_out_downgrades_to_warning; AC-5: ✓ 15 тестов + full suite 3522 passed; decision #93
