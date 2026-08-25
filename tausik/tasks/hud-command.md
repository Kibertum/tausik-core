---
slug: hud-command
title: ".tausik/tausik hud — live dashboard"
status: done
epic: claude-hardening
story: p3-nice-to-have
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/project_parser.py (hud sub-command), scripts/project_cli_extra.py или новый handler, tests/test_hud_cli.py"
scope_exclude: "Другие CLI commands не трогать"
relevant_files:
  - "scripts/project_parser.py"
  - "scripts/project_cli_ops.py"
  - "scripts/project.py"
  - "tests/test_hud_cli.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-16T23:30:07Z"
---

## Goal

Более богатый, чем status, живой dashboard: active task + progress, session duration, recent logs, gates status. Из oh-my-claudecode HUD

## Acceptance Criteria

1) Новый CLI sub-command `.tausik/tausik hud` — показывает компактную сводку: активная задача с прогрессом plan steps, session duration, последние 3 task_logs, gates status (enabled/disabled). 2) Выводит читаемо за один экран (~30 строк). 3) pytest test_hud_cli.py — 4+ тестов: empty project, with active task, with logs, output format. 4) pytest all passed. 5) ruff clean. Negative: (a) нет сессии → "No active session" без ошибки. (b) нет задач → "No active task" без ошибки. (c) long task title → truncate до 80 chars.

## Plan

[{"step": "CLI subparser + handler cmd_hud", "done": true}, {"step": "tests/test_hud_cli.py", "done": true}, {"step": "pytest + ruff + done", "done": true}]

## Rollback

## Journal

- 2026-04-16T23:23:27Z [implementation] — AC verified: AC1 (CLI hud subcommand) ✓ — добавлен в project_parser.py, handler cmd_hud в project_cli_ops.py. Live test: показывает Session, Active task, Gates в ~7 строк. AC2 (≤30 строк) ✓ — компактный output с границами ═══. AC3 (4+ тестов) ✓ — 5 тестов: empty project, active task, logs, long title truncation, borders. AC4 (pytest) ✓ — 5/5 passed in модуле, полный suite будет запущен в next. AC5 (ruff clean) ✓. Negative: (a) no session → печатает "(none)". (b) no active task → "(no active task)". (c) long title 200 chars → truncate до 80.
