---
slug: mcp-verify-is-a-second-command-not-a-second-rendering
title: "tausik_verify — вторая РЕАЛИЗАЦИЯ команды, а не второй рендеринг: квитанция, дескриптор и код выхода живут только в CLI"
status: planning
epic: release-19-renar-conformance
story: evidence-primitives
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

Ветка CLI `verify` объявляет relevant_files, обрабатывает попадание в кэш, печатает квитанцию и одноразовый verify-дескриптор и завершается кодом выхода; обработчик MCP возвращает текстовый блок со своей сводкой и своими NOTE. Это не рендеринг, который можно вынести, — это разные команды под одним именем, и схлопывание есть перепроектирование того самого пути, через который проходит закрытие по QG-2. Поэтому вынесено отдельной задачей, а не сделано наполовину. Заведено из one-implementation-per-command-mcp-over-cli (инвентарь: 17 вторых реализаций, 13 схлопнуто, эта объявлена остатком).

## Acceptance Criteria

## Plan

## Rollback

## Journal
