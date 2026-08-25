---
slug: d3-en-session-active-time
title: "docs/en/session-active-time.md NEW"
status: done
epic: docs-overhaul-v13
story: docs-en-new-features
complexity: null
role: tech-writer
stack: python
tier: light
call_budget: 25
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "docs/en/session-active-time.md"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-26T16:19:18Z"
---

## Goal

docs/en/session-active-time.md NEW: gap-based metric threshold recompute

## Acceptance Criteria

1. docs/en/session-active-time.md created; 2. Explains gap-based active vs wall clock; 3. Documents idle threshold config (session_idle_threshold_minutes); 4. Documents session recompute; 5. Documents activity hook; 6. Negative: doesn't conflate wall clock with active time

## Plan

## Rollback

## Journal

- 2026-04-26T16:19:18Z [implementation] — AC verified: 1.✓ docs/en/session-active-time.md created; 2.✓ Algorithm explained with explicit "wall vs active" pseudo-code and idle-gap rule; 3.✓ session_idle_threshold_minutes documented under Threshold Configuration table with default 10 min; 4.✓ session recompute documented under Retro Computation; 5.✓ activity_event.py hook covered in Activity Hook section; 6.✓ negative — explicit "Negative — What Active Time Is Not" section disambiguates from wall clock and tool-call proxy.
