---
slug: v14b-doc-gen-test-count
title: "B6 follow-up: gen_doc_constants extension — pytest test_count via --collect-only"
status: done
epic: null
story: null
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 45
defect_of: null
scope: "scripts/pytest_test_count.py, scripts/gen_doc_constants.py, tests/test_gen_doc_constants.py, docs/_generated/constants.json, AGENTS.md, CHANGELOG.md, CHANGELOG.ru.md"
scope_exclude: "scripts/audit_translation_drift.py, scripts/docs_lint.py, scripts/mcp_tool_counts.py, agents/*, .claude/*"
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-06T22:08:41Z"
---

## Goal

Расширить scripts/gen_doc_constants.py: посчитать реальное число тестов через `pytest --collect-only -q --override-ini="addopts="` (total, без fast-lane filter), записать в constants.json как `test_count`. Cross-file scanner для упоминаний `(\d+) tests` в docs (AGENTS, README, CHANGELOG исключён). Исправить найденные дрифты (AGENTS.md показывает 2226, реально 3050). Закрывает deferred TODO #4 из v14b-doc-gen-cross-files handoff.

## Acceptance Criteria

1. Новый модуль `scripts/pytest_test_count.py` с функцией `count_tests(repo_root) -> int`: запускает `pytest --collect-only -q --override-ini="addopts="` через subprocess (timeout=60s, stdin=DEVNULL — gotcha #88), парсит финальную строку `N tests collected`, возвращает int.
2. constants.json получает новый ключ `test_count`. Существующая схема (mcp_*, tausik_version) сохраняется; sort_keys=True.
3. Cross-file scanner в gen_doc_constants.py расширен паттерном `\b(\d+)\s+tests?\b` для упоминаний test count в docs (с context-tight guard: исключить "200 tool calls", "180-min", "26+ tests" и подобные False-positive контексты — точный регекс с word boundaries).
4. CHANGELOG.md и CHANGELOG.ru.md исключены из cross-file scan (там исторические упоминания "1095 → 2246 tests" должны сохраниться).
5. Новый CLI флаг `--skip-test-count` опт-аут только для test-count check (preserves version-ref + MCP-counts).
6. tests/test_gen_doc_constants.py: +5 новых тестов для test-count scanner: (a) clean при match; (b) drift detection; (c) fenced code skip; (d) `--skip-test-count` flag isolation; (e) build_constants включает test_count в payload.
7. Драйфы исправлены: AGENTS.md "pytest suite (2226 tests)" → актуальное (3050 total) или (2930 fast lane)+(3050 total). Решение по форме — на месте, согласно scanner verdict.
8. CHANGELOG.md + CHANGELOG.ru.md entry под Unreleased v1.4.0 polish Phase B (новая запись, не правит старые).
9. Negative: pytest full suite green; ruff + mypy clean; pre-commit gates pass; existing v14b-doc-gen-cross-files + v14b-doc-gen-mcp-tool-counts behavior сохраняется (старые тесты untouched).
10. NOT in scope: skill count cross-check; hooks count cross-check; docs_lint.py refresh с новыми stale patterns (отдельный followup если нужно).

## Plan

## Rollback

## Journal

- 2026-05-06T22:08:41Z [implementation] — AC verified: 1. scripts/pytest_test_count.py (52 lines): subprocess pytest --collect-only -q --override-ini='addopts=' with stdin=DEVNULL+timeout=60s; ValueError on non-zero exit or missing summary. 2. constants.json получил test_count=3056 (sort_keys preserved); build_constants_doc сохраняет prior value при collection failure (graceful degradation). 3. scan_test_counts walks 8 targets (CHANGELOG исключены): 4 narrow patterns — pytest suite (N tests), badge URL tests-N%20passed, badge label [!N tests], **N tests** bold. 4. Patterns deliberately narrow → 'Never add 5 tests' (illustrative) НЕ flag. 5. CLI --skip-test-count изолирует scan; --skip-cross-files skip all three. 6. Tests: +6 PASSED (clean, pytest-suite drift, badge URL+label drift, fenced-code skip, illustrative-numbers safety, --skip-test-count isolation). 7. Real drifts fixed: README.md+README.ru.md badges 2590→3056, AGENTS.md repo-layout pytest suite (2590 tests)→3056. AGENTS drift был внутри fenced code-block — manual fix kept (scanner intentionally fence-blind для false-positive control). 8. CHANGELOG.md + CHANGELOG.ru.md entries добавлены в top of Unreleased v1.4.0 polish Phase B Added section. 9. Verify: pytest 22/22 gen_doc_constants PASSED; ruff All checks passed; mypy Success no issues; translation_drift OK; gen_doc_constants --check OK. 10. NOT in scope respected: skill count + hooks count + docs_lint refresh остаются follow-up'ами.
