---
slug: fix-risk-compute-stdin-hang
title: "[defect] risk_compute git без stdin=DEVNULL → MCP task_done hang (реинтродукция v14b-defect-mcp-task-done-stdin-hang)"
status: done
epic: null
story: null
complexity: simple
role: developer
stack: null
tier: null
call_budget: null
defect_of: v15-risk-compute-on-done
scope: "scripts/risk_compute.py (1 строка stdin), tests/test_risk_compute_stdin.py (регресс + class-guard)"
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-13T12:09:59Z"
---

## Goal

risk_compute._git_numstat_lines гонит git diff/log --numstat на каждом task_done без stdin=DEVNULL. Под MCP stdin=JSON-RPC пайп → git блокируется/съедает протокол → hang. Тот же класс, что фикс v14b в verify_git_diff.py.

## Acceptance Criteria

1. risk_compute._git_numstat_lines: subprocess.check_output несёт stdin=subprocess.DEVNULL (как verify_git_diff.py). 2. Регресс-тест: git-вызов risk_compute проходит stdin=DEVNULL (мок check_output, проверка kwargs). 3. Анти-регресс класса: тест сканирует MCP-достижимые модули scripts/ на subprocess-вызовы без stdin=DEVNULL — fail если найден незащищённый. 4. Negative/boundary: git отсутствует или timeout → _factor_code_churn возвращает None без исключения (except-ветка); stdin-фикс не ломает обработку ошибок. 5. pytest green; ruff clean.

## Plan

## Rollback

## Journal

- 2026-06-13T12:08:48Z [implementation] — Root cause (regression): risk_compute (v15-risk-compute-on-done) добавил git-subprocess без stdin=DEVNULL, переоткрыв класс v14b-defect-mcp-task-done-stdin-hang; verify_git_diff.py имел защиту, новый код её не унаследовал. Prevention: class-guard тест test_risk_compute_stdin сканирует все scripts/ top-level subprocess-вызовы на stdin=DEVNULL — ловит реинтродукцию автоматически.
- 2026-06-13T12:09:59Z [implementation] — AC: 1. ✓ risk_compute._git_numstat_lines несёт stdin=subprocess.DEVNULL (risk_compute.py:46-58). 2. ✓ test_git_call_passes_stdin_devnull — мок check_output, kwargs['stdin'] is DEVNULL. 3. ✓ class-guard TestNoUnguardedSubprocessInMcpPath — AST-скан scripts/ top-level, 0 нарушений (доп. защитил verify_receipt_emit.py + cli_push_ok.py). 4. ✓ test_git_failure_returns_none — TimeoutExpired → None без исключения. 5. ✓ pytest 299 passed (risk/verify/receipt/task_done), ruff clean.
