---
slug: metrics-disclose-method-and-thresholds-carry-a-basis
title: "Метрики раскрывают метод вместе с цифрой, пороги несут основание, пересечение эскалируется (SENAR 1.5 §9.4)"
status: done
epic: release-110-deferred-from-19
story: release110-senar-15-claimed-honestly
complexity: medium
role: backend
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/metric_methods.py"
  - "scripts/render_metrics.py"
  - "scripts/backend_queries_metrics.py"
  - "scripts/status_view.py"
  - "scripts/project_cli_metrics.py"
  - "scripts/project_parser_ops.py"
  - "harness/skills/end/SKILL.md"
  - "tests/test_metric_methods.py"
scope_paths:
  - "scripts/metric_methods.py"
  - "scripts/render_metrics.py"
  - "scripts/backend_queries_metrics.py"
  - "scripts/status_view.py"
  - "scripts/project_cli_metrics.py"
  - "scripts/project_parser*.py"
  - "scripts/project_config.py"
  - "harness/claude/mcp/project/*.py"
  - "harness/skills/end/SKILL.md"
  - "tests/*.py"
  - "docs/ru/*.md"
  - "docs/en/*.md"
  - "CHANGELOG*.md"
scope_tools: []
depends_on: []
completed_at: "2026-09-23T19:10:18Z"
resolution: null
resolution_reason: null
tracker_refs:
  - "github#179"
started_model_id: claude-fable-5-1
started_model_version: null
done_model_id: null
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
---

## Goal

SENAR 1.5 §9.4 — новый раздел: (a) метод раскрывается с цифрой (популяция, тип записи, период), (b) цифра из самодельных записей меряет записанное, а не произошедшее, и не подаётся как мера произошедшего, (c) самоустановленный порог несёт основание и данные, (d) пересечённый порог эскалируется, а не двигается тихо. tausik metrics печатает Throughput 5.72, FPSR 91.2%, DER 9.5% без популяции и периода; цели «FPSR >85%», «DER <5%» живут в скилле end без основания; DER 9.5% выше цели 5% — и об этом никто не эскалировал. Цель: каждая метрика печатается с методом, каждая цель — со ссылкой на основание, каждое пересечение — событием.

## Acceptance Criteria

1. tausik metrics (и MCP) печатает для каждой SENAR-метрики: популяцию (какие записи), период, формулу; тест сравнивает вывод с реестром метрик.
2. Оговорка (b) печатается один раз для класса самодельных записей (FPSR, DER, Manual Intervention Rate) — не как лозунг, а с именем записи, от которой цифра зависит.
3. Цели/пороги вынесены в конфиг или реестр с полем basis (текст + дата + команда замера); скилл end читает цели оттуда; НЕГАТИВНЫЙ: цель без basis — тест красный.
4. Пересечение цели пишет событие metric_target_crossed один раз на период; status показывает открытые пересечения (§9.4(d)); НЕГАТИВНЫЙ: изменение цели без записи основания — отказ команды.
5. НЕГАТИВНЫЙ: метрика с нулевой популяцией печатает «популяции нет», а не 0%.
6. docs/ru+en metrics; CHANGELOG EN+RU.

## Plan

## Rollback

git revert; события остаются в журнале (append-only).

## Journal

- 2026-09-23T18:32:07Z [implementation] — Сделано: scripts/metric_methods.py (METHODS, DEFAULT_TARGETS с основанием, targets, figure, crossed, escalate, method_lines, set_target); get_metrics отдаёт populations; render_metrics печатает блок §9.4 и 'no population'; metrics target --basis (обязателен); скилл end цитирует цели из отчёта; docs cli en/ru. Живой прогон: DER 9.4% -> CROSSED, одно событие metric_target_crossed записано. Поправка: attempts растёт на start/unblock, красный verify его не двигает — формулировка записи исправлена. 7 тестов tests/test_metric_methods.py зелёные, 37 соседних метрик зелёные.
- 2026-09-23T19:05:07Z [implementation] — Шаг 2: реестр дополнен manual_intervention (самодельная запись); цели несут basis + measured_on + measured_by; open_crossings; status_view показывает открытые пересечения (WARNING Metric target crossed … der=9.4 — на живом проекте) и исправлена формулировка аудита: 'task closures since last audit' вместо 'sessions' (остаток задачи каденции). 12 тестов tests/test_metric_methods.py зелёные, 51 тест status/audit/mcp зелёный. AC verified: 1. ✓ test_every_registered_method_is_printed_as_registered, test_report_discloses_method_population_period_and_self_made_records 2. ✓ строка 'Self-made records' один раз для класса с именем записи (fpsr, der, dead_end_rate, manual_intervention) 3. ✓ DEFAULT_TARGETS с basis/датой/командой, test_every_default_target_carries_basis_date_and_command; НЕГАТИВНЫЙ test_override_without_basis_is_not_used_and_says_so; скилл end цитирует отчёт 4. ✓ test_crossing_is_escalated_once_and_cleared_on_recovery, test_status_escalates_an_open_crossing; НЕГАТИВНЫЙ test_set_target_refuses_without_basis_and_records_with_one 5. ✓ НЕГАТИВНЫЙ test_empty_population_is_reported_as_absent_not_zero 6. ✓ docs cli en/ru, CHANGELOG EN+RU.
