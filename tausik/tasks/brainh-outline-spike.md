---
slug: brainh-outline-spike
title: "[P2] Spike: Outline как alt-backend brain"
status: planning
epic: brain-hardening
story: brainh-core
complexity: medium
role: architect
stack: null
tier: moderate
call_budget: 40
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

Техдолг #2 аудита (TODO 2026-04-22): оценить Outline (self-hosted wiki) как альтернативу Notion — снимает зависимость от внешнего SaaS (риск #11 аудита: sanctions/access). Time-boxed spike: API-возможности, миграция данных, adapter-интерфейс (brain уже config-agnostic — memory #37). AC: вывод go/no-go с обоснованием; при go — спека adapter; dead end задокументирован при no-go.

## Acceptance Criteria

## Plan

## Rollback

## Journal

- 2026-07-20T10:40:43Z [planning] — КАНДИДАТ НА ЗАКРЫТИЕ (решение #153, сессия #120). Спайк ищет замену внешнему SaaS-субстрату, а shared-knowledge вообще убирает Notion из критического пути, понижая его до необязательного публикатора. После этого вопрос 'чем заменить Notion как субстрат' теряет предмет: субстратом становится локальная БД, а публикатор по определению необязателен.
