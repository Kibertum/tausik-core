---
slug: v14-finalize-changelog-header
title: "Поправить устаревшую шапку CHANGELOG (5 done → 10 done)"
status: done
epic: null
story: null
complexity: null
role: tech-writer
stack: python
tier: trivial
call_budget: 8
defect_of: null
scope: "CHANGELOG.md, CHANGELOG.ru.md (только шапка релиза 1.4.0)"
scope_exclude: "всё остальное в CHANGELOG ниже шапки, любые .py файлы, docs/, agents/, scripts/"
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-02T21:46:56Z"
---

## Goal

Шапка релиза v1.4.0 в CHANGELOG.md (стр 19-24) и CHANGELOG.ru.md (стр 21-25) говорит «28 of 35 backlog tasks landed across 5 completed epics, 5 epics remain partially complete with 7 hygiene/audit tasks deferred to 1.4.x» — это устарело. Реальность: все 10 v14-* эпиков done в БД, Phase B выполнена пост-Composer (скрипты audit/hygiene/check_docs + project_cli_hygiene + тесты лежат в untracked). Шапка должна сказать «All 10 v14-* epics closed; full backlog landed». Обновить EN + RU зеркало синхронно.

## Acceptance Criteria

1. CHANGELOG.md строки 19-24: «28 of 35 backlog tasks landed across 5 completed epics… 5 epics remain partially complete with 7 hygiene/audit tasks deferred to 1.4.x» заменено на корректный текст про закрытые 10 эпиков и приземлённый полный backlog.
2. CHANGELOG.ru.md строки 21-25: то же самое для русского зеркала.
3. Список 5 closed epics в скобках расширен до полных 10: brain-snippets, model-prompts, verify-integrity, cost-telemetry, framework-lean, project-hygiene, test-philosophy, doc-automation, dead-code-audit, skill-store.
4. Семантика «pulled in by Composer batch + Phase B follow-up» сохранена.
5. Никаких других секций CHANGELOG не тронуто (negative: pytest на не-CHANGELOG файлах не падает; diff показывает только CHANGELOG.md и CHANGELOG.ru.md).
6. Negative scenario: если случайно дёрнуть строки до 19 или после 24 — diff не содержит других правок (контроль через git diff после правки).
relevant_files: CHANGELOG.md, CHANGELOG.ru.md

## Plan

## Rollback

## Journal

- 2026-05-02T21:46:53Z [implementation] — AC verified: 1. CHANGELOG.md строки 19-24 заменены (всё про 5/35 → All 10 epics) — diff показал точное изменение шапки + добавил список 10 эпиков. 2. CHANGELOG.ru.md строки 21-25 — то же самое для русского зеркала. 3. Список 10 эпиков в скобках присутствует: brain-snippets, model-prompts, verify-integrity, cost-telemetry, framework-lean, project-hygiene, test-philosophy, doc-automation, dead-code-audit, skill-store. 4. Композер batch + Phase B follow-up семантика сохранена. 5. git diff CHANGELOG.md CHANGELOG.ru.md показывает только изменение шапки и обновление section-headings (Verify-First infrastructure / Verify-First инфраструктура — было 'Added' / 'Добавлено'). 6. Negative: scope ограничен 2 файлами, остальные .py не тронуты.
