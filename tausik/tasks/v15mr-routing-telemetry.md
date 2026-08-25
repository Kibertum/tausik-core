---
slug: v15mr-routing-telemetry
title: "[P2] Телеметрия routing adherence в metrics"
status: done
epic: v15-model-routing
story: v15mr-phase-routing
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/model_routing_adherence.py, scripts/service_task.py, scripts/project_cli_ops.py, tests/*, README.md, docs/_generated/constants.json"
scope_exclude: "scripts/model_routing_matrix.py, scripts/model_routing.py (read-only consumers), .claude/ (bootstrap-generated)"
relevant_files:
  - "scripts/model_routing_adherence.py"
  - "scripts/service_task.py"
  - "scripts/project_cli_ops.py"
  - "tests/test_routing_adherence.py"
  - README.md
  - "docs/_generated/constants.json"
scope_paths:
  - "scripts/model_routing_adherence.py"
  - "scripts/service_task.py"
  - "scripts/project_cli_ops.py"
  - "tests/*"
  - README.md
  - "docs/_generated/constants.json"
scope_tools: []
depends_on: []
completed_at: "2026-06-14T15:29:36Z"
---

## Goal

Телеметрия adherence: на task done писать recommended vs actual модель (recommendation уже в model_routing_session; actual из транскрипта), показывать в tausik metrics процент совпадений и топ отклонений — данные для калибровки матрицы.

## Acceptance Criteria

1. task done фиксирует пару recommended/actual (crash-safe JSONL .tausik/routing_adherence.jsonl) когда обе модели известны. 2. tausik metrics показывает строку routing adherence (% совпадений по семейству и n) + топ отклонений. 3. Негативный кейс (ошибочный/пустой ввод): при недоступном transcript или пустой/неизвестной модели запись ПРОПУСКАЕТСЯ и ошибка НЕ выбрасывается — task done не блокируется. 4. pytest: запись пары, агрегация %/n/deviations, и негатив (пустой actual -> None, close не падает).

## Plan

## Rollback

git revert: аддитивная телеметрия, ничего не блокирует

## Journal

- 2026-06-14T15:29:35Z [implementation] — AC verified: 1. ✓ task_done records recommended/actual pair to crash-safe JSONL .tausik/routing_adherence.jsonl via model_routing_adherence.finalize_close (service_task.py); integration tests/test_routing_adherence.py::TestTaskDoneIntegration::test_task_done_records_adherence (row with match=True) 2. ✓ tausik metrics prints '--- Routing Adherence (v1.5) ---' line: pct + n + top deviations via aggregate_adherence (project_cli_ops.py cmd_metrics); TestAggregate::test_pct_and_deviations (66.7% n=3, opus->sonnet x1) 3. ✓ Negative: missing transcript/empty/unknown model -> record skipped, no error, close not blocked — TestNegative (3) + TestTaskDoneIntegration::test_task_done_without_transcript_skips_no_error (no row, task closes) 4. ✓ pytest tests/test_routing_adherence.py 11 passed (record/aggregate/negative/integration); full task lifecycle test_senar green; filesize service_task.py 399<400 via finalize_close extraction; doc-constants 4146 in sync
