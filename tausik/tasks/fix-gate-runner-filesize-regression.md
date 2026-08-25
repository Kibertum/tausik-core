---
slug: fix-gate-runner-filesize-regression
title: "Defect: gate_runner.py 405>400 — извлечь filesize-gate в свой модуль"
status: done
epic: null
story: null
complexity: simple
role: developer
stack: python
tier: light
call_budget: 15
defect_of: align-filesize-gate-research-exemption
scope: "Новый scripts/gate_filesize.py; scripts/gate_runner.py (удалить перемещённое, добавить re-export). НЕ трогать: gate_stack_dispatch импорт, прочие gate-функции, логику filesize."
scope_exclude: "gate_command_runner, gate_stack_dispatch, run_gates логику"
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-14T00:30:23Z"
---

## Goal

Регрессия от align-filesize-gate-research-exemption: gate_runner.py был ровно 400 строк, +5 строк (research-exempt) → 405, нарушает hard-лимит. Извлечь когезивный filesize-gate (count_lines, _FILESIZE_EXEMPT_DIRS/BASENAMES, _normalize_path, run_filesize_gate) в новый gate_filesize.py; gate_runner re-export count_lines+run_filesize_gate для тестов и run_gates-диспатча. Это и устраняет хрупкость «gate_runner ровно на грани».

## Acceptance Criteria

1. gate_runner.py < 400 строк (было 405). 2. gate_filesize.py содержит count_lines, exempt-константы, _normalize_path, run_filesize_gate. 3. gate_runner re-export count_lines+run_filesize_gate (tests `from gate_runner import ...` и run_gates-диспатч работают без правок тестов). 4. Negative/boundary: файл 500 строк вне exempt → passed=False; research-файл → passed=True (оба теста зелёные). 5. Root cause задокументирован: gate_runner был на грани 400, любой add ломал; экстракция убирает хрупкость. 6. filesize-gate проходит для всех source-файлов репо (репо-wide проверка пуста). 7. pytest test_gates зелёный, ruff чист.

## Plan

## Rollback

git checkout scripts/gate_runner.py + rm scripts/gate_filesize.py. Чистое перемещение — откат тривиален.

## Journal

- 2026-06-14T00:30:22Z [implementation] — AC-1: ✓ gate_runner.py 405→328 (<400). AC-2: ✓ gate_filesize.py (92) с count_lines/exempt-константами/_normalize_path/run_filesize_gate. AC-3: ✓ gate_runner re-export (from gate_runner import count_lines,run_filesize_gate работает; run_gates-диспатч ок) — tested via tests/test_gates.py. AC-4: ✓ Negative: 500-строчный non-research→False, research→True (test_filesize_gate_non_research_md_still_blocks + test_filesize_gate_exempts_research_dir). AC-5: ✓ root cause: gate_runner был ровно на 400, любой add ломал; экстракция убрала хрупкость. AC-6: ✓ репо-wide filesize-проверка пуста (0 violations). AC-7: ✓ pytest 94 passed, ruff clean. Domain: filesize-gate поведение неизменно.
