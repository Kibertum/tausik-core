---
slug: kb-global-write
title: "Запись в общую базу: флаг global у memory, decide, snippet"
status: planning
epic: shared-knowledge
story: kb-global
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths:
  - "scripts/service_knowledge.py"
  - "scripts/knowledge_db.py"
scope_tools: []
completed_at: null
---

## Goal

Флаг --global у команд memory add, decide и работы со сниппетами направляет запись в общую базу вместо проектной. Ничего не спрашивать интерактивно: явный флаг и всё. Запись сохраняет пометку проекта-источника — на своей машине скрывать нечего, и это пригодится для ранжирования и для будущего авто-повышения. Скраббер здесь НЕ нужен: приватность переезжает на границу выгрузки в Notion.

## Acceptance Criteria

1. Флаг --global у memory add, decide и работы со сниппетами направляет запись в общую базу; без флага запись идёт в проектную. Тест проверяет обе ветки.
2. Флаг не запускает интерактивный диалог — маршрут определяется только явным флагом.
3. Запись в общую базу сохраняет пометку проекта-источника.
4. Скраббер на этом пути не вызывается (приватность переезжает на границу публикации в Notion).
CHANGELOG.md [Unreleased] и зеркало CHANGELOG.ru.md обновлены прозаической записью об этом изменении.

## Plan

## Rollback

git revert; записи снова только в проектную БД

## Journal
