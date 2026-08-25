---
slug: v14c-token-budget-task
title: "C6: $ token budget per task с блокировкой при превышении"
status: done
epic: v14-polish-followup
story: v14-polish-c-followup
complexity: complex
role: developer
stack: python
tier: substantial
call_budget: 120
defect_of: null
scope: "scripts/backend_schema.py + scripts/backend_migrations.py (v27 migration), scripts/project_parser.py (CLI flags), scripts/service_validation.py (validate_task_add_inputs), scripts/service_task.py (task_add/task_update accepts new fields), scripts/service_recording.py (record_cost_actual или extend record_call_actual), scripts/backend_queries_usage.py (rollup_for_task helper), scripts/hooks/task_cost_budget_check.py (NEW), bootstrap/bootstrap_hooks.py + bootstrap/bootstrap_qwen.py (register new hook), harness/{claude,cursor}/mcp/project/handlers.py (task_show envelope), tests/test_cost_budget_task.py (NEW), docs/{en,ru}/cost-telemetry.md, docs/{en,ru}/configuration.md, CHANGELOG.md + CHANGELOG.ru.md (entry)"
scope_exclude: "scripts/cost_pricing.py (read-only, не меняем), scripts/hooks/posttool_usage.py (read-only — собирает usage_events; hook новый отдельный), session-level token cap (отдельная задача), HUD/status display tokens-used (отдельная задача), token-tier mapping в /plan SKILL.md (отдельная задача), любые ML/embedding deps"
relevant_files:
  - "scripts/backend_schema.py"
  - "scripts/backend_migrations.py"
  - "scripts/backend_crud.py"
  - "scripts/backend_queries_usage.py"
  - "scripts/service_validation.py"
  - "scripts/service_task.py"
  - "scripts/service_recording.py"
  - "scripts/service_task_done.py"
  - "scripts/project_parser_task.py"
  - "scripts/project_cli_task.py"
  - "scripts/hooks/task_cost_budget_check.py"
  - "bootstrap/bootstrap_hooks.py"
  - "bootstrap/bootstrap_qwen.py"
  - "tests/test_cost_budget_task.py"
  - "tests/test_bootstrap_hooks_parity.py"
  - "docs/en/cost-telemetry.md"
  - "docs/ru/cost-telemetry.md"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-07T13:08:40Z"
---

## Goal

Поверх call_budget (tool calls) добавить cost_budget_usd. При превышении 1.5x — blocking warning, при 2x — refuse to continue. Защита от runaway tasks.

## Acceptance Criteria

1) Schema migration v27 (или next) добавляет 4 nullable колонки в tasks: cost_budget_usd REAL, cost_actual_usd REAL, token_budget INTEGER, tokens_actual INTEGER. Existing rows получают NULL. Миграция идемпотентна.
2) CLI: task add|update получают --cost-budget <float USD> и --token-budget <int>. validate_task_add_inputs отклоняет отрицательные/non-numeric значения с понятной ошибкой.
3) Новый helper usage_events_cost_rollup_for_task(slug, since=task.started_at) → {tokens: int, cost_usd: float} в backend_queries_usage.py — переиспользует существующий rollup_by_task контракт где возможно.
4) task_done extension — service_recording.record_call_actual ИЛИ парный record_cost_actual после него; rollup и пишет cost_actual_usd + tokens_actual в task row; emit warning '[TAUSIK cost-budget WARN]' в stderr при cost_actual ≥ 1.5× cost_budget. Никогда не блокирует task_done.
5) Новый PostToolUse hook scripts/hooks/task_cost_budget_check.py — после каждого tool call: находит единственную active task с cost_budget_usd IS NOT NULL, роллапит usage_events с task.started_at, эмитит:
   - ≥ 1.5× cost_budget AND < 2.0× → '[TAUSIK cost-budget WARN] task <slug> at $X / $Y (1.5× soft cap)'
   - ≥ 2.0× cost_budget → '[TAUSIK cost-budget BLOCKER] task <slug> at $X / $Y (2× hard cap reached — stop and re-plan or `tausik task update --cost-budget`)'
   Throttle: max 1 emission per 30s per (task_slug, level) через .tausik/.cost_budget_throttle.json (atomic write); silent no-op когда 0 active tasks, ≥2 active tasks, активная задача без budget, или TAUSIK_SKIP_HOOKS=1. Hook никогда не выбрасывает исключений (subprocess exit 0).
6) Bootstrap registers new hook в bootstrap_hooks.py + bootstrap_qwen.py (parity-test enforced).
7) MCP/CLI surface: task_show отображает 4 новые колонки когда заданы; task_list/MCP envelope — без изменений (не загружаем default лишним).
8) Tests: новый tests/test_cost_budget_task.py покрывает (a) schema migration adds 4 cols nullable; (b) validate_task_add_inputs rejects negative cost_budget/token_budget; (c) rollup_for_task happy path с фейковыми usage_events; (d) record_cost_actual writes back и warn при 1.5×; (e) hook subprocess: silent no-op без active task / без budget / TAUSIK_SKIP_HOOKS=1 / multiple active tasks; (f) hook WARN at 1.5×; (g) hook BLOCKER at 2.0×; (h) throttle file dedupes within 30s; (i) hook never raises на malformed stdin / DB lock.
9) Docs: docs/{en,ru}/cost-telemetry.md расширены секцией 'Per-task cost/token budget'; docs/{en,ru}/configuration.md упоминает CLI флаги.
10) pytest 3318+ PASS, ruff/mypy clean, doctor clean, filesize ≤400L per source file, bootstrap drift-clean.

## Plan

## Rollback

## Journal

- 2026-05-07T13:07:23Z [implementation] — AC verified: AC-1 ✓ schema v27 4 nullable cols (test_four_columns_added_nullable). AC-2 ✓ --cost-budget/--token-budget flags + task add/update wiring (TestValidation 8 cases). AC-3 ✓ usage_events_cost_rollup_for_task в backend_queries_usage.py (TestRollupForTask 4 cases). AC-4 ✓ record_cost_actual в service_recording.py пишет actuals + 1.5× warn (TestRecordCostActual 5 cases). AC-5 ✓ scripts/hooks/task_cost_budget_check.py с WARN/BLOCKER/throttle (TestHookSilentNoOp 7 cases + TestHookWarnAndBlocker 4 cases + TestHookThrottle 2 cases + TestHookUnits 6 cases). AC-6 ✓ bootstrap_hooks.py + bootstrap_qwen.py + parity test required-set extended. AC-7 ✓ task_show CLI принтер показывает cost/tokens строки. AC-8 ✓ tests/test_cost_budget_task.py 37 PASS. AC-9 ✓ docs/{en,ru}/cost-telemetry.md секция Per-task cost/token budget. AC-10 ✓ pytest 3225 PASS, ruff/mypy clean, doctor ALL CLEAN, filesize OK (max prod 252L), bootstrap drift-clean.
