---
slug: v14-finalize-readme-counts
title: "Обновить test counts 2318 → 2585 в README/AGENTS/docs"
status: done
epic: null
story: null
complexity: null
role: tech-writer
stack: python
tier: light
call_budget: 15
defect_of: null
scope: "README.md, README.ru.md, AGENTS.md, docs/en/architecture.md, docs/ru/architecture.md — только test count числа"
scope_exclude: "CHANGELOG.md/ru.md (историческая запись), любой code, .py файлы"
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-02T22:17:14Z"
---

## Goal

README.md/README.ru.md badges + table «Tests count», AGENTS.md строка про pytest suite, docs/{en,ru}/architecture.md команда `pytest tests/ -v` — все показывают 2318. Реальный финальный pytest показал 2585 passed + 7 skipped в 6:30. Обновить значения везде. CHANGELOG.md уже корректно говорит «2318 → 2513» в Tests секции — оставить как есть (исторический record промежуточного состояния).

## Acceptance Criteria

1. README.md badge `tests-2318%20passed` → `tests-2585%20passed`.
2. README.md table «Tests count» 2318 → 2585.
3. README.ru.md badge + Тестов table 2318 → 2585.
4. AGENTS.md строка «pytest suite (2318 tests)» → «pytest suite (2585 tests)».
5. docs/en/architecture.md `# all tests (2318)` → `# all tests (2585)`.
6. docs/ru/architecture.md `# все тесты (2318)` → `# все тесты (2585)`.
7. Negative: CHANGELOG.md строка «2318 → 2513» (в Tests секции v1.4) НЕ трогать — это historical record Composer batch.
8. Negative: CHANGELOG.md строка «2270 → 2318» (в Tests секции v1.3.x) НЕ трогать.
9. Final pytest: 2585 passed, 7 skipped (validated).
relevant_files: README.md, README.ru.md, AGENTS.md, docs/en/architecture.md, docs/ru/architecture.md

## Plan

## Rollback

## Journal

- 2026-05-02T22:17:14Z [implementation] — AC verified: 1. ✓ README.md badge 2318 → 2585. 2. ✓ README.md table Test count 2585. 3. ✓ README.ru.md badge + Тестов 2585. 4. ✓ AGENTS.md строка 2585 tests. 5. ✓ docs/en/architecture.md 2585. 6. ✓ docs/ru/architecture.md 2585. 7. ✓ Negative: CHANGELOG.md '2318 → 2513' и v1.3.x '2270 → 2318' НЕ тронуты — historical record. 8. ✓ Negative: v1.3.x CHANGELOG записи не тронуты. 9. ✓ pytest финал: 2585 passed, 7 skipped (validated background run).
