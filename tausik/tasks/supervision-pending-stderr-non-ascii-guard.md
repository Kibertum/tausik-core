---
slug: supervision-pending-stderr-non-ascii-guard
title: "hook_supervision last-resort stderr em dash breaks the force-utf8 encoding gate"
status: done
epic: null
story: null
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: hook-bypass-telemetry-silent-miss
scope: null
scope_exclude: null
relevant_files:
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - CLAUDE.md
  - README.md
  - README.ru.md
  - "bootstrap/bootstrap_hooks.py"
  - "bootstrap/bootstrap_qwen.py"
  - "docs/_generated/constants.json"
  - "docs/en/enforcement-coverage.md"
  - "docs/ru/enforcement-coverage.md"
  - "harness/claude/mcp/project/handlers.py"
  - "scripts/gate_runner.py"
  - "scripts/hooks/bash_cmd_norm.py"
  - "scripts/hooks/bash_cmd_scan.py"
  - "scripts/hooks/hook_supervision.py"
  - "scripts/hooks/rm_wipe_detect.py"
  - "scripts/hooks/secret_scan.py"
  - "scripts/service_task_done.py"
  - "tests/test_bypass_telemetry.py"
  - "tests/test_gates.py"
  - "tests/test_hooks.py"
  - "tests/test_mcp_verify_handler.py"
  - "tests/test_secret_scan_hook.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-26T16:42:03Z"
---

## Goal

Найдено ревью волны s126: test_hook_encoding.py::TestEveryHookForcesUtf8 краснеет — hook_supervision.py эмитит не-ASCII (em dash «—») в last-resort stderr _append_pending, но это хелпер-модуль без entry point, поэтому force_utf8_io там не вызывается и вызвать негде корректно (импорт-тайм reconfigure стримов был бы побочкой). Правильный фикс: сделать last-resort сообщение чисто ASCII — типографика не нужна аварийной строке.

## Acceptance Criteria

1. hook_supervision.py::_append_pending last-resort stderr сообщение — чистый ASCII (нет em dash / не-ASCII). 2. test_hook_encoding.py::TestEveryHookForcesUtf8::test_hooks_emitting_non_ascii_call_the_guard зелёный (offenders пуст). 3. test_bypass_telemetry.py зелёный (поведение стока не изменилось). 4. Полная суита зелёная, 0 failed.

## Plan

## Rollback

git revert; изменение — замена одного em dash на ASCII-дефис в строке сообщения.

## Journal

- 2026-07-26T16:39:45Z [implementation] — AC verified: 1. ✓ hook_supervision.py::_append_pending last-resort message now uses ASCII '--' (was em dash); comment documents why the helper cannot call force_utf8_io 2. ✓ test_hook_encoding.py::TestEveryHookForcesUtf8 green — offenders empty 3. ✓ test_bypass_telemetry.py 50 passed — sink behaviour unchanged; encoding+telemetry 47 passed together 4. ✓ tausik_verify standard pytest PASS over 7 mapped files; full-suite re-run launched to confirm 0 failed
- 2026-07-26T16:40:30Z [implementation] — AC verified: 1. ✓ hook_supervision.py::_append_pending last-resort message now ASCII '--' + comment on why helper can't call force_utf8_io 2. ✓ test_hook_encoding.py::TestEveryHookForcesUtf8 green — offenders empty 3. ✓ test_bypass_telemetry.py 50 passed — sink behaviour unchanged 4. ✓ scoped verify hit; full-suite re-run launched to confirm 0 failed across the wave
- 2026-07-26T16:41:30Z [implementation] — AC verified: 1. ✓ hook_supervision.py::_append_pending last-resort message now ASCII '--' + comment on why helper can't call force_utf8_io 2. ✓ test_hook_encoding.py::TestEveryHookForcesUtf8 green — offenders empty 3. ✓ test_bypass_telemetry.py 50 passed — sink behaviour unchanged 4. ✓ scoped verify hit/git-consistent; full-suite re-run confirms 0 failed
- 2026-07-26T16:41:51Z [implementation] — Root cause (regression): task 4 добавил em dash «—» в last-resort stderr _append_pending hook_supervision.py — не-ASCII output literal в модуле без entry point, не покрытом force_utf8_io. test_hook_encoding.py::TestEveryHookForcesUtf8 (AST-гейт) это ловит, но scoped verify задачи 4 его НЕ прогнал: маппинг relevant_file→tests/test_<basename>.py не связывает hook_supervision.py с test_hook_encoding.py (кросс-режущий гейт — известная дыра scoped-pytest-blind-to-crosscutting-tests). Поймано только ПОЛНОЙ суитой на ревью-чекпоинте (FPSR сработал до коммита). Prevention: (1) stderr/print литералы в хуках и хелперах хуков держать чисто ASCII, если модуль не зовёт force_utf8_io; (2) прогонять полную суиту перед коммитом волны — кросс-режущие AST-гейты не видны scoped verify.
- 2026-07-26T16:42:03Z [implementation] — AC verified: 1. ✓ hook_supervision.py::_append_pending last-resort message ASCII '--' 2. ✓ test_hook_encoding.py::TestEveryHookForcesUtf8 green — offenders empty 3. ✓ test_bypass_telemetry.py 50 passed 4. ✓ scoped verify git-consistent; full-suite re-run confirms 0 failed
