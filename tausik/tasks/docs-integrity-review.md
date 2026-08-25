---
slug: docs-integrity-review
title: "Полное ревью целостности и перелинкованности документации"
status: done
epic: final-polish
story: final-cleanup
complexity: medium
role: tech-writer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "docs/, references/, README.md, README.ru.md, CLAUDE.md, AGENTS.md, CHANGELOG.md"
scope_exclude: null
relevant_files:
  - CLAUDE.md
  - AGENTS.md
  - README.md
  - README.ru.md
  - CONTRIBUTING.md
  - "references/architecture.md"
  - "references/architecture.en.md"
  - "docs/en/architecture.md"
  - "docs/ru/architecture.md"
  - "scripts/README.md"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-08T15:28:23Z"
---

## Goal

Проверить все docs на: битые ссылки, устаревшие числа/версии, пропущенные перекрёстные ссылки, синхронность RU/EN, полноту покрытия

## Acceptance Criteria

1. Все внутренние ссылки между docs работают (нет битых)
2. Числа (тесты, tools, skills, файлы) актуальны во всех docs
3. EN и RU версии синхронны по содержанию
4. Все перекрёстные ссылки между docs/, references/, CLAUDE.md, README корректны
5. Нет orphan-документов без ссылок из оглавлений
6. Ссылки на несуществующие файлы или секции возвращают ошибку при проверке — все исправлены

## Plan

## Rollback

## Journal

- 2026-04-08T15:25:37Z [implementation] — AC verified: 1. All internal links valid (0 broken) ✓ 2. Test count 914→918 in 11 files ✓ 3. EN/RU fully synced (13+13 files, 1 minor editorial diff in senar-compliance-matrix) ✓ 4. All cross-refs between docs/, references/, CLAUDE.md, README correct ✓ 5. No orphan docs — all indexed in docs/README.md ✓ 6. Architecture tables updated with all 27 scripts (was 17), line counts refreshed ✓
