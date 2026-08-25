---
slug: brain-init-orphan-cleanup
title: "MEDIUM: cleanup guidance при failure после create_brain_databases"
status: done
epic: null
story: null
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: brain-decide-auto-route
scope: "scripts/brain_init.py, tests/test_brain_init.py"
scope_exclude: "scripts/brain_project_registry.py, scripts/brain_config.py"
relevant_files:
  - "scripts/brain_init.py"
  - "tests/test_brain_init.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-24T20:05:17Z"
---

## Goal

При failure save_config/register_project после создания 4 DB пользователь получает orphan Notion databases без hint. Обернуть post-create в try/except, печатать created database_ids для manual cleanup или registrer before API call

## Acceptance Criteria

1. run_wizard оборачивает пост-create_brain_databases секцию (registry + merge + save) в try/except
2. При exception: io.print выводит 4 созданных database_ids (category -> id) с guidance о manual cleanup
3. Исключение пере-raise-ится как WizardError с сообщением про orphan databases
4. Happy path не регрессирует — существующий test_run_wizard_non_interactive_success зелёный
5. Ошибка/граничный случай: register_project raise RegistryLockError после успешного create → orphan cleanup guidance + WizardError
6. Ошибка/граничный случай: config_ops.save raise OSError после успешного create+register → orphan cleanup guidance
7. Guidance включает все 4 database_ids, не только один (чтобы пользователь мог их всех найти)
8. pytest tests/test_brain_init.py проходит; ruff clean

## Plan

## Rollback

## Journal

- 2026-04-24T20:01:52Z [implementation] — AC verified: новый _print_orphan_cleanup_guidance(io, db_ids, exc) печатает все 4 category: id (title) с инструкцией Archive via Notion UI. Пост-create секция (register + all_project_names + save) обёрнута в try/except — при любой ошибке печатается guidance и raise-ится WizardError(Post-create step failed). 3 новых теста: registry_failure_prints_orphan_guidance (RegistryLockError), config_save_failure_prints_orphan_guidance (OSError disk full), happy_path_prints_no_orphan_guidance (regression). Все 11 существующих брейн-init-тестов PASS. pytest 28/28. ruff clean.
