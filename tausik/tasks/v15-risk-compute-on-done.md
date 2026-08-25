---
slug: v15-risk-compute-on-done
title: "[P1] Расчёт + хранение risk-score при task_done"
status: done
epic: v15-evidence-attestation
story: v15-risk-score
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "risk_compute.py (сбор факторов) + миграция v31 + вызов в service_task_done"
scope_exclude: "risk_model.py (заморожен, decision #92), service_gates.py"
relevant_files:
  - "scripts/risk_compute.py"
  - "scripts/service_task_done.py"
  - "scripts/backend_schema.py"
  - "scripts/backend_migrations.py"
  - "scripts/project_backend.py"
  - "tests/test_risk_compute.py"
scope_paths:
  - "scripts/risk_compute.py"
  - "scripts/service_task_done.py"
  - "scripts/backend_schema.py"
  - "scripts/backend_migrations.py"
  - "scripts/project_backend.py"
  - "scripts/project_cli_task.py"
  - "tests/*"
scope_tools: []
depends_on: []
completed_at: "2026-06-12T01:33:55Z"
---

## Goal

Вычислять risk-score (по модели v15-risk-model) на task_done и сохранять в БД при задаче. Не блокирует закрытие сам по себе — даёт градацию доверия для downstream (story E, метрики).

## Acceptance Criteria

1. task_done после прохождения гейтов считает risk (risk_model.compute_risk) из собранных факторов и сохраняет tasks.risk_score REAL + tasks.risk_json TEXT (миграция v31); в notes строка Risk: <score> (<level>). 2. Расчёт НЕ блокирует закрытие: негативный сценарий — ошибка сбора факторов/git недоступен -> задача закрывается, risk опускается или фактор уходит в defaulted=1.0, исключение наружу не летит. 3. Факторы: gate_coverage из receipt последнего verify-рана vs конфиг verify-гейтов; test_delta/security из relevant_files; ac_evidence из service_ac_evidence.build_report; churn из git numstat (diff HEAD + log --since started_at). 4. Негативный: битые/отсутствующие relevant_files или AC -> консервативные значения по контракту модели, без падения. 5. pytest: интеграция task_done пишет score/json/note + unit collector + не-блокирование при сломанном git.

## Plan

## Rollback

git revert: колонки v31 аддитивны (NULL = не считалось), расчёт best-effort и не блокирует закрытие; откат не требует миграции вниз

## Journal

- 2026-06-12T01:33:54Z [implementation] — AC verified: 1-5 OK см. лог (миграция v31, best-effort расчёт, 33+114 тестов).
- 2026-06-12T01:33:54Z [implementation] — AC-1: ✓ tests/test_risk_compute.py::TestTaskDoneIntegration::test_done_persists_risk_and_note (score+json+note); AC-2 Negative: ✓ test_done_survives_risk_crash (закрытие при упавшем коллекторе); AC-3: ✓ TestCollector::test_collects_without_db_receipt_or_git (receipt/relevant_files/AC/git факторы); AC-4 Negative: ✓ test_broken_git_drops_churn_only + test_total_failure_returns_none; AC-5: ✓ 10 тестов + regression done/risk 114 passed
