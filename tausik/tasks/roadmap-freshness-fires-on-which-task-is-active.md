---
slug: roadmap-freshness-fires-on-which-task-is-active
title: "Свежесть карты релиза срабатывает на ТЕКУЩЕЙ активной задаче, а не на остатке — красное на файле, который никто не менял"
status: planning
epic: release-19-renar-conformance
story: evidence-primitives
complexity: simple
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

ROADMAP.md печатает остаток по статусам («planning 4» / «active 1, planning 3»), поэтому START любой задачи делает закоммиченную карту устаревшей, и полный прогон краснеет на файле, которого никто не трогал. Предмет карты — ЧТО ОСТАЛОСЬ в релизе, а не кто что держит прямо сейчас (это отвечает `tausik team`). Дефект заведён внутри one-implementation-per-command-mcp-over-cli: обнаружен полным прогоном сразу после старта задачи, в ту же смену, когда карта была сделана (roadmap-artifact-predates-decision-256). Чинить внутри чужой задачи не стал — предмет другой.

## Acceptance Criteria

## Plan

## Rollback

## Journal
