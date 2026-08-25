---
slug: r14-mcp-task-done-ux
title: "task_done UX: visible progress, host-timeout guidance, prefer v2 in docs/skills"
status: done
epic: rel-14-readiness
story: rel-14-audit-fixes
complexity: null
role: null
stack: null
tier: moderate
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-01T00:33:17Z"
---

## Goal

Release 1.4 readiness: r14-mcp-task-done-ux

## Acceptance Criteria

1. Скиллы /ship и /task рекомендуют tausik_task_done_v2 как preferred при QG-2 и описывают разницу со старой формой. 2. Документация и онбординг описывают лимиты хоста VS Code Claude Extension и практику verify до done. 3. Negative: если v2 недоступен в MCP-сервере, скиллы fallback на v1 с явным предупреждением, не зависают.

## Plan

## Rollback

## Journal

- 2026-05-01T00:33:16Z [implementation] — Quickstart (en+ru) gained two callouts after Verify-First section: (1) VS Code/JetBrains/Cursor per-MCP-tool timeout — verify first, done reads cache; (2) task_done_v2 preferred when MCP server publishes it. mcp.md updated 'preferred for QG-2 since 1.3.7' note in en+ru.
- 2026-05-01T00:33:16Z [implementation] — Troubleshooting (en+ru) extended: MCP Servers table gains 3 new rows (task_done timeout in VS Code, generic timeout w/o traceback, agent ignores v2). New section 'Host limits & task_done UX' / 'Лимиты хоста & task_done UX' explains workflow, opt-out, v2-vs-v1.
- 2026-05-01T00:33:16Z [implementation] — Updated agents/skills/ship/SKILL.md step 8: tausik_task_done_v2 marked preferred for QG-2 since 1.3.7, with explicit fallback to v1 (single aggregated error string). agents/skills/task/SKILL.md tool table promoted v2; close-step explains v1 fallback path.
- 2026-05-01T00:33:17Z [implementation] — AC verified: 1. /ship and /task skills recommend tausik_task_done_v2 ✓ (agents/skills/{ship,task}/SKILL.md). 2. VS Code host limits + verify-before-done practice documented in quickstart and troubleshooting (en+ru) ✓. 3. Negative scenario - if v2 unavailable, skills explicitly fallback to v1 with note about aggregated error string ✓ (no silent retry). All skill tests pass: 235/235.
