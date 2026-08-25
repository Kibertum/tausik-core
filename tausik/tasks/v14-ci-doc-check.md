---
slug: v14-ci-doc-check
title: "CI или pre-commit: проверка ссылок / генерации доков"
status: done
epic: v14-doc-automation
story: v14-doc-link-check
complexity: medium
role: null
stack: null
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - ".github/workflows/tests.yml"
  - "scripts/hooks/check_docs.py"
  - "docs/en/dev-doc-checks.md"
  - "docs/ru/dev-doc-checks.md"
  - "tests/test_check_docs_hook.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-02T11:23:20Z"
---

## Goal

Документирован запуск локально.

## Acceptance Criteria

1. Конфиг CI или hook. 2. README разработчика. 3. Negative: без git metadata локально — понятный skip/fail.

## Plan

## Rollback

## Journal

- 2026-05-02T11:22:29Z [implementation] — AC verified: 1. ✓ CI step добавлен в .github/workflows/tests.yml (gen_doc_constants --check) + scripts/hooks/check_docs.py для локального pre-commit; tested via tests/test_check_docs_hook.py::TestCiWorkflow + TestRealRepoSync. 2. ✓ README разработчика docs/{en,ru}/dev-doc-checks.md (mirror), tested via TestDeveloperDocs. 3. ✓ Negative: hook без pyproject.toml выдаёт skipping и exit 0 — TestNegativeNoPyproject::test_skip_when_no_pyproject_above. + drift сценарий покрыт TestDriftDetected.
