---
slug: metrics-tier-calibration
title: "Metrics: per-tier FPSR + avg call_actual для calibration"
status: done
epic: agent-native-planning
story: estimation-planning-integration
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/backend_queries.py (extend get_metrics)\nscripts/project_cli.py (cmd_metrics output formatting)\nscripts/project_cli_extra.py (если cmd_status там — добавить drift строку)\ntests/test_metrics_tier.py (новый)"
scope_exclude: "scripts/service_*.py (не нужны изменения)\nagents/skills/* (отдельно)\nbackfill старых задач (вне scope — задачи без tier остаются NULL и попадают в 'unset')"
relevant_files:
  - "scripts/backend_queries.py"
  - "scripts/backend_tier_metrics.py"
  - "scripts/project_cli_ops.py"
  - "scripts/project_cli.py"
  - "tests/test_metrics_tier.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-25T12:10:07Z"
---

## Goal

tausik metrics показывает: per-tier FPSR (trivial/light/.../deep), avg call_actual vs avg call_budget per tier, drift indicator (если actual systematically выше budget — пороги нуждаются в калибровке). tausik status строкой "Last 10 tasks: avg actual/budget ratio 1.2 (overestimating budget)". Foundation для long-term calibration loop. Включает миграцию старых задач — backfill tier='moderate' по умолчанию для legacy.

## Acceptance Criteria

- [ ] backend.get_metrics() возвращает dict["per_tier"] = { tier: {count, avg_actual, avg_budget, fpsr_pct, ratio_actual_over_budget} } для всех 5 тиров (включая 'unset' для legacy без tier)
- [ ] backend.get_metrics() возвращает dict["calibration_drift"] = последний 10 done тасков, средний ratio (actual/budget) — индикатор "underestimating" если >1.3, "overestimating" если <0.7, "calibrated" иначе; None если меньше 5 measured tasks
- [ ] CLI tausik metrics показывает таблицу per-tier (count, avg_budget, avg_actual, fpsr) + строку drift
- [ ] CLI tausik status строкой добавляет calibration drift indicator (если drift !=None)
- [ ] Backwards-compat: задачи без tier отображаются как 'unset' bucket; без call_actual попадают в counts но не в avg
- [ ] Negative scenarios: 0 done tasks → empty per_tier dict (не падает с ZeroDivisionError); все tier=NULL → drift=None
- [ ] Tests tests/test_metrics_tier.py: (a) per_tier breakdown с разнотиплированными задачами; (b) calibration_drift с разными ratio; (c) пустая БД; (d) только legacy задачи без tier; (e) CLI metrics output содержит "Per-tier" headline

## Plan

## Rollback

## Journal

- 2026-04-25T12:10:06Z [implementation] — AC verified: 1. backend per_tier dict с count/avg_actual/avg_budget/fpsr/ratio ✓ (TestPerTier 4 PASSED) 2. calibration_drift label + avg_ratio + samples ✓ (TestCalibrationDrift 5 PASSED) 3. CLI tausik metrics показывает Per-tier таблицу + drift строку ✓ (TestCliMetricsOutput PASSED) 4. CLI tausik status добавляет Calibration строку при наличии drift ✓ (project_cli.py edit) 5. Backwards-compat — задачи без tier попадают в 'unset', без actual avg=None ✓ (test_legacy_tasks_bucketed_as_unset PASSED) 6. Negative scenarios: empty DB → empty per_tier ✓ (test_empty_db_returns_empty_dict); все no actual → drift=None ✓ (test_skips_tasks_without_actual) 7. Tests test_metrics_tier.py 10/10 PASSED + смежные test_tausik_backend 64/64 PASSED
