---
slug: docs-hooks-rewrite
title: "Hooks.md complete rewrite — 20 hooks, 3 missing, wrong section assignments"
status: done
epic: null
story: null
complexity: medium
role: developer
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
completed_at: "2026-05-15T13:29:07Z"
---

## Goal

hooks.md: (1) total 17+1=18 → 20+1=21. (2) Добавить 3 missing PostToolUse: posttool_usage, tool_output_truncation_nudge, task_cost_budget_check. (3) Fix matcher typo line 30 (двойной tausik_task_done + bogus Bash). (4) brain_search_proactive — переместить из UserPromptSubmit в PreToolUse (WebSearch|WebFetch matcher). (5) session_metrics → SessionEnd, session_cleanup_check → Stop.

## Acceptance Criteria

(1) Все числовые правки соответствуют constants.json или прямому подсчёту в коде. (2) pnpm build clean. (3) Содержание не утеряно. (4) Ошибка: не должно остаться никаких устаревших чисел/имён.

## Plan

## Rollback

## Journal

- 2026-05-15T13:29:07Z [implementation] — AC verified: правки сделаны, pnpm build clean 4.63s.
