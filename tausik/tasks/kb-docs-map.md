---
slug: kb-docs-map
title: "Карта затронутой документации и разбиение на зоны для роя"
status: planning
epic: shared-knowledge
story: kb-docs
complexity: medium
role: architect
stack: null
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths:
  - docs
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

ПОДГОТОВКА К РОЮ, без неё рой бесполезен. Составить карту всех мест в docs/ru и docs/en, затронутых переходом: shared-brain (281 строка, переписывается почти целиком), architecture, cli, mcp, agent-contract, quickstart, configuration, README на двух языках. Разбить на НЕПЕРЕСЕКАЮЩИЕСЯ зоны — по одному владельцу на файл, иначе параллельные агенты будут править один файл и затирать друг друга. Отдельно выписать сквозные утверждения, которые встречаются в нескольких документах и должны измениться согласованно: где живут знания, нужен ли Notion, как настраивается общая база, что можно и нельзя выгрузить в git. Учесть doc-drift гейты и счётчики в constants.json — они тоже часть карты.

## Acceptance Criteria

1. Составлена карта всех мест в docs/ru и docs/en, затронутых переходом (shared-brain, architecture, cli, mcp, agent-contract, quickstart, configuration, README ru+en).
2. Файлы разбиты на НЕПЕРЕСЕКАЮЩИЕСЯ зоны — по одному владельцу на файл.
3. Сквозные утверждения, встречающиеся в нескольких документах (где живут знания, нужен ли Notion, как настраивается общая база, что можно и нельзя выгрузить в git), выписаны отдельным списком для согласованного изменения.
4. Doc-drift гейты и счётчики в constants.json учтены в карте.
CHANGELOG.md [Unreleased] и зеркало CHANGELOG.ru.md обновлены прозаической записью об этом изменении.

## Plan

## Rollback

карта это артефакт планирования; откат не требуется

## Journal
