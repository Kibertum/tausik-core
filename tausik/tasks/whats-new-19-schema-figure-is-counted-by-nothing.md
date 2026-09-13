---
slug: whats-new-19-schema-figure-is-counted-by-nothing
title: "whats-new 1.9 говорит «схема БД 44 → 58, четырнадцать миграций», а дерево несёт SCHEMA_VERSION = 61"
status: planning
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
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

ЗАМЕР, смена #251: docs/en/whats-new-1.9.md:84 «Database schema: 44 → 58. Fourteen migrations apply automatically», docs/ru/whats-new-1.9.md:83 «Схема БД: 44 → 58. Четырнадцать миграций»; scripts/backend_schema.py: SCHEMA_VERSION = 61; `git show v1.8.0:scripts/backend_schema.py` → 44. Три миграции (v59 model_id сессии, v60, v61 tracker_refs) легли после того, как абзац был написан, и ничто его не пересчитывает — конвенция #673: число в документе обязано быть сосчитано чем-то, иначе гниёт молча. Тест tests/test_release_notes_1_9.py уже считает записи Unreleased; он получает вторую проверку: фигура «44 → N» на обеих страницах равна SCHEMA_VERSION, а число миграций прописью равно N − 44 (базовая 44 — литерал с комментарием: это свойство опубликованного тега v1.8.0, который в CI может отсутствовать). Текст абзаца обновляется на 61 и семнадцать; заодно абзац называет v61 (tracker_refs) как вторую заметную миграцию, потому что она добавила колонку, которую пост-миграция v43 стирала — уже починенный дефект, о котором апгрейдящемуся стоит знать.

## Acceptance Criteria

AC-1: обе страницы whats-new-1.9 называют «44 → 61» и «семнадцать/seventeen» миграций. AC-2: tests/test_release_notes_1_9.py читает SCHEMA_VERSION из scripts/backend_schema.py и сверяет с фигурой на обеих страницах; число миграций прописью сверяется с N − 44. AC-3: мутация — вернуть 58 на одной странице — краснит тест (доказано прогоном). AC-4: signed verify.

## Plan

## Rollback

git revert.

## Journal
