---
slug: d2-en-hooks-refresh
title: "docs/en/hooks.md refresh"
status: done
epic: docs-overhaul-v13
story: docs-en-refresh
complexity: null
role: tech-writer
stack: python
tier: light
call_budget: 25
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "docs/en/hooks.md"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-26T16:16:38Z"
---

## Goal

docs/en/hooks.md refreshed with all 19 hooks

## Acceptance Criteria

1. docs/en/hooks.md lists all 19 hooks with v1.3 names; 2. PreToolUse/PostToolUse/Stop separation correct; 3. Memory pretool block hook documented; 4. Activity hook (gap-based) documented; 5. Negative: no hooks listed that don't exist in scripts/hooks/

## Plan

## Rollback

## Journal

- 2026-04-26T16:16:38Z [implementation] — AC verified: 1.✓ all 19 hooks listed with v1.3 names (mapped from `ls scripts/hooks/`); 2.✓ PreToolUse/PostToolUse/SessionStart/UserPromptSubmit/Stop/pre-commit categories separated; 3.✓ memory_pretool_block.py documented; 4.✓ activity_event.py documented (gap-based active time); 5.✓ negative — no listed hook missing from scripts/hooks/, no fictional hooks.
