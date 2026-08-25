---
slug: review-mlow-resolver-recursive
title: "[A7 MED] resolve_test_files_for_relevant: recursive walk вместо flat listdir"
status: done
epic: senar-verify-redesign
story: review-findings-mlow-fix
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/gate_runner.py, tests/test_gates.py"
scope_exclude: "scripts/service_verification.py, scripts/project_config.py"
relevant_files:
  - "scripts/gate_runner.py"
  - "tests/test_gates.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-25T10:24:50Z"
---

## Goal

Сейчас resolve_test_files_for_relevant в gate_runner.py ищет test files только в flat tests/, через os.listdir. Проекты с tests/integration/, tests/unit/, tests/e2e/ молча получают full-suite (cached as scoped — стейл). Заменить на os.walk(tests/) с тем же basename pattern.

## Acceptance Criteria

1. resolve_test_files_for_relevant использует os.walk(tests_dir) вместо os.listdir
2. Матч test_<stem>.py + test_<stem>_*.py на любой глубине под tests/
3. Регрессия: текущие flat-tests case'ы (tests/test_brain_init.py от scripts/brain_init.py) всё ещё работают
4. Новый кейс: tests/integration/test_foo.py от scripts/foo.py → matched
5. Новый кейс: tests/unit/scoped/test_bar.py от scripts/bar.py → matched
6. Дедуп между путями (если test_foo.py есть и в tests/ и в tests/integration/)
7. Ошибка/граничный случай: tests/ отсутствует → returns [] (graceful)
8. Ошибка/граничный случай: PermissionError на одной из subdir во время walk → пропустить, продолжить (не crash)
9. Тесты в test_gates.py: test_glob_subdirectory_test_files, test_dedup_same_test_in_two_dirs
10. pytest зелёный, ruff clean

## Plan

## Rollback

## Journal

- 2026-04-25T10:24:46Z [implementation] — AC verified: ✓1 os.walk(tests_root) — single-pass index by basename ✓2 test_<stem>.py + test_<stem>_*.py любая глубина ✓3 регрессия: flat tests/test_X.py всё ещё работают (test_basename_match passes) ✓4 test_glob_subdirectory_test_files: tests/integration/test_foo.py + tests/test_foo.py + tests/unit/scoped/test_bar.py ✓5 ✓6 test_dedup_when_test_appears_in_multiple_dirs ✓7 test_missing_tests_dir_returns_empty (empty index, returns []) ✓8 OSError catch для permission errors ✓9 +4 new tests in TestResolveTestFilesForRelevant ✓10 pytest 82/82, ruff clean
