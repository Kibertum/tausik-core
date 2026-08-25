---
slug: v14b-delete-smoke-tests
title: "B2: удалить 10 trivial smoke tests (assert callable / is not None без behavior check)"
status: done
epic: v14-polish-quality
story: v14-polish-b-quality
complexity: null
role: qa
stack: python
tier: trivial
call_budget: 10
defect_of: null
scope: "tests/test_skills_maturity.py"
scope_exclude: "tests/test_bootstrap_venv.py, tests/test_bootstrap_frontmatter.py (проверены, smoke не найдено)"
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-03T11:29:13Z"
---

## Goal

Удалить 10 worthless smoke tests: test_skills_maturity.py:317-327 (test_copy_*_function_exists — pure assert callable), test_bootstrap_venv.py:33-44 (overlapping is_not_none), test_bootstrap_frontmatter.py:20-55 (assert fields is not None без field check).

## Acceptance Criteria

1. Static scan через AST/regex показывает только 2 пустых smoke теста (не 10 как в исходной оценке): tests/test_skills_maturity.py L317 (test_copy_roles_function_exists) и L323 (test_copy_stacks_function_exists), оба `assert callable(import-name)` без behaviour check.
2. Удалены оба теста + класс TestBootstrapRolesStacks reorganized или сокращён (если остаются полезные тесты — оставить).
3. Анализ остальных кандидатов из исходной оценки задокументирован в notes:
   - test_bootstrap_venv.py L33-44 — НЕ smoke: test_finds_something имеет 2 ассерта (is not None + isabs), test_found_version_sufficient идёт глубже (version >= MIN_PYTHON). Перекрытие минимально, оставляем.
   - test_bootstrap_frontmatter.py L20-55 — НЕ smoke: каждый тест включает специфичные field assertions (name=="test", context=="fork", etc.) или негативные сценарии (no frontmatter / missing file).
4. Pytest: -2 теста (2591 → 2589 в полном suite). Оставшиеся 2589 зелёные.
5. Lint: ruff All checks passed.
6. Negative: для следующего scan той же regex'ой `Found 0 pure-smoke test methods` (целевой кейс полностью устранён).

## Plan

[{"step": "AST/regex scan \u0434\u043b\u044f \u0432\u0441\u0435\u0445 smoke \u043a\u0430\u043d\u0434\u0438\u0434\u0430\u0442\u043e\u0432 (\u2713 done, 2 \u043d\u0430\u0439\u0434\u0435\u043d\u043e)", "done": true}, {"step": "\u0423\u0434\u0430\u043b\u0438\u0442\u044c 2 \u0442\u0435\u0441\u0442\u0430 \u0438\u0437 test_skills_maturity.py", "done": true}, {"step": "Pytest scoped + \u0440\u0435-scan", "done": true}, {"step": "Pol\u043d\u044b\u0439 pytest + ruff", "done": true}, {"step": "verify + task done", "done": true}]

## Rollback

## Journal

- 2026-05-03T11:20:00Z [implementation] — Static AST/regex scan: only 2 pure-smoke methods across all tests/. Original estimate was 10. Codebase is cleaner than expected. Scanned with: pattern matches def test_X(): with body containing ONLY `assert callable(X)` / `assert hasattr(X)` / `assert <var>[is not None]`. Excludes import lines + sys.path lines. Found: - tests/test_skills_maturity.py:317 test_copy_roles_function_exists - tests/test_skills_maturity.py:323 test_copy_stacks_function_exists Verified that the next test in the same class (test_copy_stacks_filters_by_detected) actually exercises copy_stacks() — so the smoke methods are pure import-confirmation noise. Other candidates from original goal: - test_bootstrap_venv.py L33-44: test_finds_something has 2 assertions (is not None + isabs); test_found_version_sufficient checks version >= MIN_PYTHON. Each adds value. NOT smoke. - test_bootstrap_frontmatter.py L20-55: every test verifies specific field values or negative scenarios (no frontmatter / missing file). NOT smoke.
- 2026-05-03T11:29:13Z [implementation] — AC verified: AC-1 ✓ static AST/regex scan нашёл только 2 (не 10) pure-smoke методов (см. notes для критерия). AC-2 ✓ удалены test_copy_roles_function_exists (L317) + test_copy_stacks_function_exists (L323) из tests/test_skills_maturity.py + объяснительный комментарий что behaviour test ниже покрывает функции. AC-3 ✓ остальные кандидаты (test_bootstrap_venv L33-44, test_bootstrap_frontmatter L20-55) проанализированы и НЕ удалены — каждый тест содержит специфичные field assertions или негативные сценарии (см. task_log). AC-4 ✓ pytest полный suite: 2591 passed, 7 skipped в 8m26s (baseline после defect 2593 → −2). Scoped tests/test_skills_maturity.py: 170 passed (был 172, −2). AC-5 ✓ ruff: All checks passed. AC-6 ✓ re-scan той же regex: Found 0 pure-smoke methods (целевой класс 100% устранён).
