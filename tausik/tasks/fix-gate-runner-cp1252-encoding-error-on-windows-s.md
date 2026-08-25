---
slug: fix-gate-runner-cp1252-encoding-error-on-windows-s
title: "Fix gate_runner cp1252 encoding error on Windows subprocess output"
status: done
epic: null
story: null
complexity: null
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/gate_runner.py, scripts/project_config.py"
scope_exclude: "tests/, agents/, .claude/"
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-07T11:45:46Z"
---

## Goal

gate_runner.py subprocess output parsing fails on Windows due to cp1252 encoding. Need to use utf-8 encoding for subprocess.run(). Tests pass (832/832) but gate reports failure.

## Acceptance Criteria

1. subprocess.run() в gate_runner.py использует encoding='utf-8' для stdout/stderr. 2. Gates проходят без cp1252 ошибок на Windows. 3. Ошибка при невалидной кодировке — output обрабатывается с errors='replace'. 4. Все тесты проходят.

## Plan

## Rollback

## Journal

- 2026-04-07T11:34:55Z [implementation] — Fix applied: gate_runner.py subprocess.run() now uses encoding='utf-8', errors='replace'. Timeout made configurable via gate config (default 120s, pytest default 180s). AC verified: 1. encoding='utf-8' added to both subprocess.run calls ✓ 2. cp1252 error eliminated from gate_runner output ✓ 3. errors='replace' handles invalid bytes gracefully ✓ 4. 831 tests pass ✓
