---
slug: v2-engine-standalone-package
title: "[2.0] Engine как standalone pip-пакет; .claude/ → опциональный IDE-адаптер"
status: planning
epic: v2-global-mcp
story: v2gm-packaging
complexity: complex
role: architect
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
completed_at: null
---

## Goal

96 MCP-инструментов самодостаточны (подтверждено исследованием). Вынести backend в pip-устанавливаемый пакет; хуки/скиллы/brain → опциональный адаптер, не хард-зависимость. Починить хрупкий путь CLI-wrapper к .claude/scripts/ (резолвить из установленного пакета). Связано с decision #94.

## Acceptance Criteria

## Plan

## Rollback

## Journal
