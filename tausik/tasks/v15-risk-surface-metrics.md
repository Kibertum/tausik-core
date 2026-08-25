---
slug: v15-risk-surface-metrics
title: "[P2] Risk-score в metrics/status"
status: done
epic: v15-evidence-attestation
story: v15-risk-score
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "risk_metrics.py + секция в cmd_metrics + строка в cmd_status"
scope_exclude: null
relevant_files:
  - "scripts/risk_metrics.py"
  - "scripts/project_cli_ops.py"
  - "scripts/project_cli.py"
  - "tests/test_risk_metrics.py"
scope_paths:
  - "scripts/risk_metrics.py"
  - "scripts/project_cli_ops.py"
  - "scripts/project_cli.py"
  - "tests/*"
scope_tools: []
depends_on: []
completed_at: "2026-06-12T01:37:37Z"
---

## Goal

Показывать risk-score в tausik metrics и status (распределение, high-risk закрытия). Связать с SENAR DER/FPSR для трендов качества.

## Acceptance Criteria

1. tausik metrics: секция Closure Risk — count/avg/распределение low-medium-high/последние high-risk слаги; рядом с DER/FPSR для трендов. 2. tausik status (полный, не compact): одна строка Risk при наличии данных. 3. Негативный: нет ни одной строки с risk_score (пустой проект/pre-v31) -> секция и строка не печатаются, ошибки нет. 4. pytest: summary-агрегация + пустой случай.

## Plan

## Rollback

git revert: чистая read-only выборка + вывод, ничего не пишет

## Journal

- 2026-06-12T01:37:23Z [implementation] — AC-1: ✓ live tausik metrics секция Closure Risk (count/avg/dist/high); AC-2: ✓ live tausik status строка Risk: avg 0.3296 over 1 closes; AC-3 Negative: ✓ test_empty_returns_none + test_unscored_rows_ignored (секция не печатается); AC-4: ✓ tests/test_risk_metrics.py 8 passed
- 2026-06-12T01:37:36Z [implementation] — AC verified: 1. OK metrics секция (live). 2. OK status строка (live). 3. OK пустой случай без вывода (тесты). 4. OK 8 тестов.
