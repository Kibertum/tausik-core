---
slug: v15-roadmap-2-0-todo
title: "2.0 roadmap в TODO.md — публичный план global-MCP + 1.x трек"
status: done
epic: v15-release-polish
story: v15-polish-public
complexity: simple
role: tech-writer
stack: null
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-13T13:07:10Z"
---

## Goal

Расписать чёткий публичный 2.0-план в TODO.md: global-MCP (gmcp-*/decision #94: request-time DB routing, standalone pip-пакет, миграция с сабмодуля), + пост-1.5 1.x-трек (snippet/orchestrator/v15mr/v16r-RENAR/brainh). Источники: gmcp-*/v2-* задачи + tausik_systemwide_analysis.md. Люди должны понимать вектор проекта.

## Acceptance Criteria

1. TODO.md содержит секцию 2.0 (global-MCP): цель, ключевые задачи gmcp-* с краткими описаниями, связь с decision #94 + tausik_systemwide_analysis.md. 2. Секция «пост-1.5 1.x трек»: snippet/orchestrator/v15mr/v16r-RENAR/brainh сгруппированы. 3. Понятно стороннему читателю (публичный проект): что, зачем, в каком порядке. 4. Negative/boundary: НЕ ломать существующую структуру TODO.md (если есть текущие пункты — сохранить/интегрировать, не затереть); markdown валиден.

## Plan

## Rollback

## Journal

- 2026-06-13T13:07:10Z [implementation] — AC: 1.✓ TODO.md секция '2.0 — Global MCP' с целью (spawn-time→request-time), таблицей gmcp-* (10 задач) + v2-* engine-work, связь decision #94 + systemwide_analysis. 2.✓ секция 'Post-1.5 1.x track': snippet(5)/orchestrator/v15mr(4)/v16r-RENAR(8)/brainh(5) сгруппированы. 3.✓ читаемо для внешнего читателя (intro + why + порядок). 4.✓ существующее сохранено (Post-Release/Brain/notify_on_done интегрированы, не затёрты); markdown валиден. Checklist: scope=TODO.md, no security surface, edge-case existing-content-preserved.
