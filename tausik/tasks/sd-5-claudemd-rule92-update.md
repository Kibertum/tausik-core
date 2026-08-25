---
slug: sd-5-claudemd-rule92-update
title: "CLAUDE.md Rule 9.2: document active-time semantics + threshold"
status: done
epic: v13-mcp-and-discipline
story: session-duration-fix
complexity: null
role: tech-writer
stack: python
tier: trivial
call_budget: 10
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - CLAUDE.md
  - "scripts/project_config.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-26T00:52:49Z"
---

## Goal

Update CLAUDE.md SENAR Rule 9.2 line to explain 180-min limit is now active time (gap-threshold 10 min), not wall clock. Document config knob `.tausik/config.json` session_idle_threshold_minutes.

## Acceptance Criteria

## Plan

## Rollback

## Journal

- 2026-04-26T00:52:49Z [planning] — AC verified: 1. CLAUDE.md hard constraint line for Rule 9.2 rewritten to clarify ACTIVE time semantics (v1.3 change) ✓ 2. SENAR Compliance table Rule 9.2 row updated with 'active time (gap-based, threshold 10 мин)' wording ✓ 3. Threshold config knob documented: .tausik/config.json under session_idle_threshold_minutes ✓ 4. session recompute CLI mentioned for retro-analysis ✓ 5. project_config.DEFAULT_SESSION_IDLE_THRESHOLD_MINUTES constant added with comment cross-referencing backend_session_metrics ✓ NEGATIVE: docs explicitly clarify wall vs active to prevent regression to old semantics ✓
