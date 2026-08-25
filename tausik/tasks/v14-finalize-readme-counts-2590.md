---
slug: v14-finalize-readme-counts-2590
title: "Bump test count badges 2585 → 2590 после relaxed cache tests"
status: done
epic: null
story: null
complexity: null
role: tech-writer
stack: python
tier: trivial
call_budget: 10
defect_of: null
scope: "README.md, README.ru.md, AGENTS.md, docs/{en,ru}/architecture.md"
scope_exclude: "CHANGELOG.md/ru.md, code, tests"
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-03T08:21:36Z"
---

## Goal

После v14-cache-relaxed-mismatch-hit добавлено 5 новых тестов (TestRelaxedMismatchCacheHit). Финальный full pytest показал 2590 passed (вместо 2585). Обновить badges и table values в README.md, README.ru.md, AGENTS.md, docs/{en,ru}/architecture.md.

## Acceptance Criteria

1. README.md badge tests-2585 → tests-2590.
2. README.md table «Test count» 2585 → 2590.
3. README.ru.md badge + Тестов table 2585 → 2590.
4. AGENTS.md «pytest suite (2585 tests)» → 2590.
5. docs/en/architecture.md `# all tests (2585)` → 2590.
6. docs/ru/architecture.md `# все тесты (2585)` → 2590.
7. Negative: CHANGELOG записи историй (2318 → 2513) НЕ трогаются.
8. Final pytest: 2590 passed, 7 skipped in 6:38 (validated).
relevant_files: README.md, README.ru.md, AGENTS.md, docs/en/architecture.md, docs/ru/architecture.md

## Plan

## Rollback

## Journal

- 2026-05-03T08:21:36Z [implementation] — AC verified: 1. ✓ README.md badge tests-2590. 2. ✓ README.md table 2590. 3. ✓ README.ru.md badge + Тестов 2590. 4. ✓ AGENTS.md 2590 tests. 5. ✓ docs/en/architecture.md 2590. 6. ✓ docs/ru/architecture.md 2590. 7. ✓ Negative: CHANGELOG history rows untouched. 8. ✓ Final pytest: 2590 passed, 7 skipped in 6:38.
