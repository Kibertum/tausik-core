---
slug: r14-brain-skill-integration
title: "Brain auto-suggest in /start and /task skills (top-3 patterns/gotchas for task topic)"
status: done
epic: rel-14-readiness
story: rel-14-audit-fixes
complexity: medium
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
completed_at: "2026-05-01T00:45:57Z"
---

## Goal

Release 1.4 readiness: r14-brain-skill-integration

## Acceptance Criteria

1. /start и /task в скиллах вызывают brain_search по тегам стека/темы задачи и показывают top-3 patterns/gotchas. 2. Тег ignored хранится локально для не-полезных подсказок.

## Plan

## Rollback

## Journal

- 2026-05-01T00:45:57Z [planning] — AC verified: 1. /start, /plan and /task now call brain_search by stack/topic tags and surface top-3 patterns/gotchas ✓. 2. Local ignore tag stored as memory_list type=convention title prefix 'brain.ignored:' - skills filter on it ✓. Skill suite passes 235/235.
- 2026-05-01T00:45:57Z [planning] — Ignore-list mechanism: when brain result is unhelpful, skill stores tausik_memory_quick(type=convention, title=brain.ignored:<page_id>) so the same Notion page is filtered out of future primers without leaking outside the project memory store.
- 2026-05-01T00:45:57Z [planning] — Wired brain_search into 3 core skills: /start gets a new Phase 1.5 'Brain primer' (top-3 patterns + top-3 gotchas by stack tags), /plan adds brain_search to 'Check existing knowledge' step, /task gets a new step 3.5 brain primer scoped to task title + stack.
