---
slug: story-add-duplicate-slug-is-a-traceback-not-a-refusal
title: "story add с существующим slug падает сырым traceback (sqlite3.IntegrityError) вместо отказа с текстом"
status: done
epic: release-110-deferred-from-19
story: release110-open-defects
complexity: simple
role: backend
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/service_hierarchy.py"
  - "scripts/service_task.py"
  - "tests/test_duplicate_slug_is_a_refusal.py"
scope_paths:
  - "scripts/service_hierarchy.py"
  - "scripts/service_task.py"
  - "scripts/project_backend.py"
  - "scripts/project_cli.py"
  - "tests/*.py"
  - "CHANGELOG*.md"
scope_tools: []
depends_on: []
completed_at: "2026-09-23T20:15:38Z"
---

## Goal

Замер смены #266: tausik story add release-110-deferred-from-19 <существующий slug> ... завершается кодом 1 и полным traceback из project_backend._ins (UNIQUE constraint failed: stories.slug). Пользователь CLI получает стек, а не ответ «история уже есть»; агент, скриптующий создание, не может отличить дубль от поломки без разбора текста исключения. Нулевая толерантность к тихим и сырым ошибкам CLI. Цель: дубль slug у story add (и epic add, task add — проверить тем же тестом) — валидационный отказ одной строкой с именем существующей сущности и кодом 1, без traceback.

## Acceptance Criteria

1. Воспроизведено тестом ДО правки: story add с существующим slug поднимает IntegrityError наружу.
2. После правки: story add / epic add / task add с существующим slug печатают отказ одной строкой (имя сущности, существующий slug) и возвращают код 1; traceback отсутствует.
3. НЕГАТИВНЫЙ: отказ не создаёт и не изменяет ничего (число строк до и после равно; тест).
4. НЕГАТИВНЫЙ: другие IntegrityError (например, несуществующий epic у story add) по-прежнему различимы своим текстом, а не схлопнуты в один.
5. CHANGELOG EN+RU.

## Plan

## Rollback

git revert

## Journal

- 2026-09-23T20:12:43Z [implementation] — AC-1: ✓ tests/test_duplicate_slug_is_a_refusal.py::test_a_duplicate_is_refused_in_one_line_and_changes_nothing
- 2026-09-23T20:12:43Z [implementation] — Воспроизведено тестом до правки: epic/story/task add с существующим slug — sqlite3.IntegrityError UNIQUE constraint failed (3 красных). Правка: ProjectService._new_slug(kind, slug) — validate_slug + проверка существования, ServiceError одной строкой; вызывается вместо validate_slug в epic_add/story_add/task_add (service_task.py остался 499 строк). Живой прогон: 'Error: Story ... already exists — pick another slug', exit=1.
- 2026-09-23T20:12:44Z [implementation] — AC-2: ✓ tests/test_duplicate_slug_is_a_refusal.py::test_a_duplicate_is_refused_in_one_line_and_changes_nothing
- 2026-09-23T20:12:44Z [implementation] — AC-3: ✓ tests/test_duplicate_slug_is_a_refusal.py::test_a_duplicate_is_refused_in_one_line_and_changes_nothing (счёт строк до=после)
- 2026-09-23T20:12:44Z [implementation] — AC-4: ✓ tests/test_duplicate_slug_is_a_refusal.py::test_a_missing_epic_is_still_its_own_refusal
- 2026-09-23T20:12:45Z [implementation] — AC-5: ✓ CHANGELOG EN+RU
