---
slug: bundled-root-separate-from-vendored-copy
title: "Корень фреймворка не отделён от вендоренной копии: хуки и MCP резолвятся из пяти разных мест"
status: planning
epic: release-19-agent-effectiveness
story: surfaces-do-not-diverge
complexity: complex
role: architect
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

РАСЩЕПЛЕНИЕ ext-p1-provider-refactor (четвёртая цель), выполнено в #189.
ФОРМУЛИРОВКА ИЗ ИСХОДНОЙ ЗАДАЧИ: «separate bundled framework root from vendored copy so hooks+MCP resolve from a single hosted location».
ЗАМЕР #189, ПОКАЗЫВАЮЩИЙ ЦЕНУ НЫНЕШНЕГО СОСТОЯНИЯ: на диске пять побайтовых копий обвязки (.claude, .cursor, .qwen, .kilo, .opencode), каждая около 359 файлов. Дрейф между ними сегодня ловит только bootstrap --check, и он ловит его ПОСЛЕ факта. Хуки и MCP каждого профиля резолвятся из СВОЕЙ копии, поэтому правка источника доезжает до исполняемого кода только через повторный bootstrap — гоча, уже стоившая нам сессии (память про MCP-сервер, держащий старый код до перезапуска).
ЧТО ДЕЛАЕТСЯ: корень фреймворка отделяется от вендоренной копии, хуки и MCP резолвятся из ОДНОГО размещения. Форма выбирается замером на Windows, где симлинки требуют прав, а не по вкусу.
СВЯЗЬ: это же снимает главный оставшийся довод задачи four-byte-identical-copies-of-the-harness, у которой все четыре заявленные издержки опровергнуты замером, — там останется только vendor_seo без источника.
НЕГАТИВНОЕ: потребительские проекты держат зеркала на своих машинах, изменение обязано нести миграцию, а не рассчитывать на переустановку.

## Acceptance Criteria

## Plan

## Rollback

Изменение размещения с миграцией для потребителей; откат git revert плюс повторный bootstrap возвращает прежнюю раскладку.

## Journal

- 2026-08-29T14:22:53Z [planning] — [#189] ПОПРАВКА К ССЫЛКЕ: задача ext-p1-provider-refactor, упомянутая выше, УДАЛЕНА 29.08 после расщепления на четыре оценённые задачи (provider-generates-artifacts-not-the-if-ide-ladder, four-ide-registries-collapse-into-one, session-model-recorded-on-non-claude-hosts, bundled-root-separate-from-vendored-copy). Ссылка сохранена как происхождение формулировок, а не как указатель на живую задачу — искать её в базе бесполезно. Найдено собственной проверкой плана: это ровно тот класс сгнившей ссылки, который чинит audit evidence.
