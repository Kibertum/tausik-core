---
slug: whats-new-19-schema-figure-is-counted-by-nothing
title: "whats-new 1.9 говорит «схема БД 44 → 58, четырнадцать миграций», а дерево несёт SCHEMA_VERSION = 61"
status: done
epic: release-19-agent-effectiveness
story: release19-effective-context
complexity: simple
role: tech-writer
stack: python
tier: light
call_budget: 20
defect_of: null
scope: "docs/en/whats-new-1.9.md, docs/ru/whats-new-1.9.md, tests/test_release_notes_1_9.py"
scope_exclude: "Схема БД и миграции не меняются; CHANGELOG не нужен (правка документации к релизу, не поведение)."
relevant_files:
  - "docs/en/whats-new-1.9.md"
  - "docs/ru/whats-new-1.9.md"
  - "tests/test_release_notes_1_9.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-09-13T11:47:42Z"
---

## Goal

ЗАМЕР, смена #251: docs/en/whats-new-1.9.md:84 «Database schema: 44 → 58. Fourteen migrations apply automatically», docs/ru/whats-new-1.9.md:83 «Схема БД: 44 → 58. Четырнадцать миграций»; scripts/backend_schema.py: SCHEMA_VERSION = 61; `git show v1.8.0:scripts/backend_schema.py` → 44. Три миграции (v59 model_id сессии, v60, v61 tracker_refs) легли после того, как абзац был написан, и ничто его не пересчитывает — конвенция #673: число в документе обязано быть сосчитано чем-то, иначе гниёт молча. Тест tests/test_release_notes_1_9.py уже считает записи Unreleased; он получает вторую проверку: фигура «44 → N» на обеих страницах равна SCHEMA_VERSION, а число миграций прописью равно N − 44 (базовая 44 — литерал с комментарием: это свойство опубликованного тега v1.8.0, который в CI может отсутствовать). Текст абзаца обновляется на 61 и семнадцать; заодно абзац называет v61 (tracker_refs) как вторую заметную миграцию, потому что она добавила колонку, которую пост-миграция v43 стирала — уже починенный дефект, о котором апгрейдящемуся стоит знать.

## Acceptance Criteria

AC-1: обе страницы whats-new-1.9 называют «44 → 61» и «семнадцать/seventeen» миграций. AC-2: tests/test_release_notes_1_9.py читает SCHEMA_VERSION из scripts/backend_schema.py и сверяет с фигурой на обеих страницах; число миграций прописью сверяется с N − 44. AC-3: НЕГАТИВ: мутация — вернуть 58 на одной странице — даёт ошибку теста (доказано прогоном). AC-4: signed verify.

## Plan

## Rollback

git revert.

## Journal

- 2026-09-13T11:47:25Z [implementation] — Сделано: заголовки «44 → 61», «Семнадцать/Seventeen» миграций, абзац о v59/v60/v61 с точной формулировкой починки пересборки v43 (после себя накладывает поздние колонки — проверено по журналу post-migration-v43-erases-every-column-added-after-it, а не по памяти). Тест TestTheSchemaFigureIsCounted: заголовок читает SCHEMA_VERSION из scripts/backend_schema.py, число прописью = N − 44 (44 — литерал: свойство тега v1.8.0, которого в CI-клоне может не быть). МУТАЦИЯ: 58 на EN-странице → 1 failed; возврат → 4 passed. Дедупликация: 290/686 = базовая.
- 2026-09-13T11:47:39Z [implementation] — AC-1 ✓ docs/en/whats-new-1.9.md:84 «Database schema: 44 → 61 … Seventeen migrations»; docs/ru/whats-new-1.9.md:83 «Схема БД: 44 → 61 … Семнадцать миграций». AC-2 ✓ tests/test_release_notes_1_9.py::TestTheSchemaFigureIsCounted::test_the_heading_ends_at_the_live_schema_version[ru|en] читает SCHEMA_VERSION из scripts/backend_schema.py; ::test_the_migration_count_in_words_matches[ru|en] сверяет слово с N − 44. AC-3 ✓ (НЕГАТИВ) мутация «58 на EN-странице» → 1 failed, возврат → 4 passed (журнал). AC-4 ✓ verify #2581 подписан. Domain: апгрейдящийся с 1.8 читает верное число миграций и узнаёт о трёх последних, включая ту, на которой поймали стирающую пересборку — число больше не гниёт, потому что его считает тест.
