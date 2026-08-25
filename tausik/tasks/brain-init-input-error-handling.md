---
slug: brain-init-input-error-handling
title: "LOW: EOFError/KeyboardInterrupt в wizard input()"
status: done
epic: null
story: null
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: brain-decide-auto-route
scope: "scripts/brain_init.py, scripts/project_cli_ops.py, tests/test_brain_init.py"
scope_exclude: "scripts/brain_project_registry.py, scripts/brain_config.py"
relevant_files:
  - "scripts/brain_init.py"
  - "scripts/project_cli_ops.py"
  - "tests/test_brain_init.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-25T09:56:31Z"
---

## Goal

Raw input() в brain_init.py падает с traceback при piped stdin + is_tty flipped. Перехватывать EOFError/KeyboardInterrupt внутри _CliIO.prompt, выдавать clean WizardError('Aborted')

## Acceptance Criteria

1. Default CliIO класс вынесен на module-level в brain_init.py (был локальный _CliIO в project_cli_ops)
2. CliIO.prompt оборачивает input() в try/except (EOFError, KeyboardInterrupt) → raise brain_init.WizardError("Aborted by user.")
3. project_cli_ops.cmd_brain использует brain_init.CliIO вместо локального _CliIO
4. Регрессия: существующие тесты wizard'а зелёные (используют _FakeIO, не CliIO — но интерфейс не меняется)
5. Ошибка/граничный случай: monkeypatch input() raise EOFError → CliIO.prompt вызывает WizardError("Aborted by user.")
6. Ошибка/граничный случай: monkeypatch input() raise KeyboardInterrupt → CliIO.prompt вызывает WizardError("Aborted by user.")
7. Happy path: monkeypatch input() возвращает строку → CliIO.prompt возвращает её без преобразований
8. pytest tests/test_brain_init.py зелёный, ruff clean

## Plan

## Rollback

## Journal

- 2026-04-25T09:56:29Z [implementation] — AC verified: 1. CliIO класс на module-level в brain_init.py ✓ 2. CliIO.prompt оборачивает input() в try/except (EOFError, KeyboardInterrupt) → WizardError("Aborted by user.") ✓ 3. project_cli_ops.cmd_brain использует brain_init.CliIO ✓ 4. existing wizard tests (28) зелёные ✓ 5. test_eof_raises_wizard_error: monkeypatch input → EOFError → WizardError ✓ 6. test_keyboard_interrupt_raises_wizard_error: → WizardError ✓ 7. test_returns_input_normally: возвращает строку ✓ 8. pytest 31/31 passed, ruff clean ✓
