---
slug: v15p-fix-hadolint-windows-head
title: "[P1] Defect: hadolint gate использует unix `head` — падает на Windows"
status: done
epic: v15-polish
story: v15p-defects
complexity: simple
role: developer
stack: python
tier: light
call_budget: 25
defect_of: null
scope: "stacks/ (gate definitions), scripts/gate_command_runner.py при необходимости, tests/"
scope_exclude: null
relevant_files:
  - "scripts/gate_command_runner.py"
  - "stacks/docker/stack.json"
  - "tests/test_gate_truncation_pipe.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-11T23:45:27Z"
---

## Goal

Найдено quality sweep 2026-06-12: gate hadolint (auto-enabled для docker stack) падает на Windows — команда содержит `head`, которого нет в cmd. Заменить на кроссплатформенный вариант (python -c / PowerShell-совместимый pipeline или ограничение вывода средствами gate runner). AC: verify --scope critical на Windows не показывает FAIL hadolint; тест на Windows-совместимость команд всех default gates (регрессия — ни один default gate не использует unix-only утилиты).

## Acceptance Criteria

1. tausik verify на Windows не показывает FAIL hadolint из-за 'head' is not recognized. 2. Регрессионный тест: ни один default/stack gate-command не использует unix-only утилиты (head, tail, grep, awk, sed, xargs) без кроссплатформенной обработки. 3. Существующие gate-тесты зелёные.

## Plan

## Rollback

## Journal

- 2026-06-11T23:45:27Z [implementation] — AC verified: 1. ✓ verify: hadolint=PASS (было FAIL 'head' is not recognized); прямой прогон на Dockerfile через runner passed=True. 2. ✓ tests/test_gate_truncation_pipe.py::test_no_stack_gate_uses_unhandled_unix_utility — все pipe-команды стеков нейтрализуемы runner'ом. 3. ✓ 108 passed (новые 18 + test_gates).
- 2026-06-11T23:45:27Z [implementation] — Root cause двухслойный: (1) '| head -30' в 19 gate-командах 12 стеков — cmd.exe не знает head/tail; (2) пустой {files} подставлялся как '.' и hadolint падал permission denied на каталоге. Фикс в gate_command_runner: _extract_truncation_filter срезает хвост '[2>&1] | head/tail -N', усечение в Python (_apply_line_filter); gate-уровневый file_patterns (fnmatch по basename) — docker/stack.json получил Dockerfile/Containerfile/*.dockerfile. E2E: verify hadolint=PASS; hadolint на реальном Dockerfile через runner passed=True. 108 passed (test_gate_truncation_pipe 18 + test_gates). pull 4a5e19f это НЕ чинил (только argv normpath/.exe-strip/utf-8).
