---
slug: auto-docs-update
title: "Auto-update project docs on /ship"
status: done
epic: dx-improvements
story: knowledge-auto
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "skills/ship/SKILL.md"
scope_exclude: null
relevant_files:
  - "agents/skills/ship/SKILL.md"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-12T16:58:59Z"
---

## Goal

При /ship после успешного коммита агент обновляет архитектурную документацию (references/) на основе diff. Скилл ship получает шаг docs-update.

## Acceptance Criteria

1. /ship после коммита предлагает обновить references/ если были структурные изменения
2. Шаг docs-update в SKILL.md скилла ship
3. Обновляются только файлы в references/, не трогает CLAUDE.md
4. Если нет структурных изменений — шаг пропускается без ошибки

## Plan

## Rollback

## Journal

- 2026-04-12T16:42:05Z [implementation] — AC verified: 1. Step 9 added to ship SKILL.md — checks structural changes ✓ 2. docs-update step in SKILL.md ✓ 3. Only references/ updated, CLAUDE.md/QWEN.md excluded ✓ 4. No structural changes = silent skip ✓
