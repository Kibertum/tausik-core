---
slug: l26-defect-escape-rate
title: "Defect escape rate: колонка есть, метрики нет"
status: done
epic: landscape-2026-h2
story: l26-provable
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/backend_defect_escape.py (новый — defect_escape_metrics + risk_backtest), scripts/backend_queries_metrics.py (вызов в get_metrics), scripts/project_cli_metrics.py или рендер metrics (секция escape rate), tests/"
scope_exclude: "Не менять схему БД (defect_of/risk_score уже есть). Не трогать формулу der (оставить для обратной совместимости). Не реализовывать полный ML-бэктест — только средние risk_score escaped vs non-escaped (сверка сигнала)."
relevant_files:
  - "scripts/backend_defect_escape.py"
  - "scripts/backend_queries_metrics.py"
  - "scripts/project_cli_ops.py"
  - "scripts/project_cli_metrics.py"
  - "tests/test_defect_escape.py"
scope_paths:
  - "scripts/backend_defect_escape.py"
  - "scripts/backend_queries_metrics.py"
  - "scripts/project_cli_ops.py"
  - "scripts/project_cli_metrics.py"
  - "tests/test_defect_escape.py"
scope_tools: []
depends_on: []
completed_at: "2026-07-20T23:46:00Z"
---

## Goal

ЕДИНСТВЕННАЯ МЕТРИКА, СПОСОБНАЯ ФАЛЬСИФИЦИРОВАТЬ УТВЕРЖДЕНИЕ ЧТО ГЕЙТЫ РАБОТАЮТ. Колонка tasks.defect_of существует (backend_schema.py:57) и используется при заведении дефект-задач, но НИЧТО не считает долю закрытий, породивших впоследствии дефект. Сейчас measured только вход (риск, калибровка бюджета), а не исход. Нужно: метрика escape rate (доля done-задач, на которые позже завёлся defect_of), с разрезами по сложности, роли, тиру и по наличию/отсутствию верификации. Дальше это позволит бэктестить risk_score против реальных исходов — сейчас риск считается при закрытии и никогда не сверяется с тем, что произошло.

## Acceptance Criteria

AC1. backend_defect_escape.defect_escape_metrics(q): escape rate = доля done-задач, на slug которых позже указал чей-то defect_of, с разрезами по complexity, role, tier и по наличию verification_run у сбежавшей задачи. Возвращает {overall, by_complexity, by_role, by_tier, by_verification}.
AC2. Каждый разрез — {escaped, done, rate_pct}; при done=0 rate_pct=0 (без деления на ноль).
AC3. risk_backtest: средний risk_score у escaped vs non-escaped done-задач (risk_score IS NOT NULL) — сверка сигнала риска с реальным исходом.
AC4. Встроено в get_metrics (ключ defect_escape); CLI metrics рендерит секцию escape rate с разрезами.
AC5. Край (негативный): пустая БД / нет дефектов / нет done-задач → все rate_pct=0, без исключения и без деления на ноль.
AC6. Регресс: существующий der не сломан; полный suite зелёный.

## Plan

## Rollback

git revert коммита. Аддитивно: новый модуль + ключ в get_metrics + рендер CLI; read-only, схему БД не трогает, откат безопасен.

## Journal

- 2026-07-20T23:44:13Z [implementation] — AC1-6 verified: AC1 ✓ defect_escape_metrics с разрезами complexity/role/tier/verification — TestEscapeRate. AC2 ✓ rate_pct=0 при done=0 без ZeroDivision — TestEdges. AC3 ✓ risk_backtest escaped vs clean avg — test_risk_backtest_separates_escaped_from_clean. AC4 ✓ встроено в get_metrics + CLI секция (смоук на живой БД: 3.7% overall). AC5 ✓ пустая БД и отсутствие verification_runs не падают — test_empty_db_is_all_zero_no_crash, test_missing_verification_table_degrades. AC6 ✓ der цел, полный suite (запускаю). Domain: на РЕАЛЬНЫХ данных метрика сразу дала фальсифицирующий сигнал — risk_score НЕ предсказывает побеги (escaped 0.33 < clean 0.38), verified сбегают чаще (селекция) — зафиксировано memory #267 для l26-provable. 7 тестов.
- 2026-07-20T23:45:59Z [implementation] — AC1-6 verified (детали в логе + memory #267). Рендер extended-metrics вынесен в project_cli_metrics (filesize: ops 423→387). 7 тестов, verify PASS.
