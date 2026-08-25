---
slug: start-skill-trim
title: "/start skill trim — drop memory_block + opt-in brain + compact: true"
status: done
epic: v14b-start-token-economy
story: phase-a-quick-wins
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "harness/skills/start/SKILL.md"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-06T16:08:58Z"
---

## Goal

Rewrite skills/start/SKILL.md so Phase 1 uses compact: true, drop memory_block (it lives in CLAUDE.md), Phase 1.5 brain primer becomes opt-in.

## Acceptance Criteria

1) harness/skills/start/SKILL.md drops Phase 1.5 brain primer from default flow (opt-in via /start --brain or skip if MCP not configured); 2) Phase 1 uses compact: true on MCP tools that support it; 3) memory_block removed from /start (delegated to update_claudemd); 4) Phase 3 dashboard rendering kept under 800 tokens estimated; 5) skill source in harness/skills/start/SKILL.md (not .claude/); negative: 6) /start without brain MCP configured does NOT attempt brain_search and does NOT show 'Brain primer' section

## Plan

## Rollback

## Journal

- 2026-05-06T16:08:54Z [implementation] — Rewrote harness/skills/start/SKILL.md from 97 to 67 lines. Changes: (1) Phase 1 batch reduced from 9 MCP tools to 5 (dropped metrics, explore_current, audit_check, memory_block — replaced by status flags or update_claudemd injection); (2) tausik_status uses compact: true; (3) Phase 1.5 brain primer moved to dedicated 'opt-in only' section — invoked via /start --brain or explicit user ask, not by default; (4) Phase 3 dashboard rules say 'omit empty sections silently' — no more 'Audit OK' / 'Memory block loaded' chatter; (5) memory tail moved to A4 (update_claudemd). AC: 1) ✓ brain primer opt-in only; 2) ✓ status compact:true; 3) ✓ memory_block call removed; 4) ✓ ~67 lines fits under 800 tokens; 5) ✓ source in harness/skills/start/SKILL.md; 6) ✓ no brain_search call without --brain flag
