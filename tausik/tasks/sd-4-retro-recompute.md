---
slug: sd-4-retro-recompute
title: "CLI: tausik session recompute (retro past 36 sessions)"
status: done
epic: v13-mcp-and-discipline
story: session-duration-fix
complexity: null
role: developer
stack: python
tier: light
call_budget: 15
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/project_cli_ops.py"
  - "scripts/project_parser_session.py"
  - "scripts/backend_session_metrics.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-26T00:57:23Z"
---

## Goal

One-shot CLI subcommand that computes active_minutes for all historical sessions and prints comparison report (wall vs active). Used to recalibrate SENAR throughput baseline.

## Acceptance Criteria

1. tausik session recompute subcommand parses --threshold/--limit/--json. 2. Output shows # | wall | active | idle% per session + TOTAL. 3. Real-data verification confirms session #35 was 478 min wall / 48 min active. NEGATIVE: empty DB prints 'No sessions to recompute', wall=0 → idle_pct '-'.

## Plan

## Rollback

## Journal

- 2026-04-26T00:52:46Z [planning] — AC verified: 1. tausik session recompute subcommand added ✓ 2. recompute_all_sessions(q,q1,threshold) added to backend_session_metrics ✓ 3. Output table: # | wall | active | idle% | started_at + TOTAL row ✓ 4. --threshold flag overrides default ✓ 5. --limit shows last N ✓ 6. --json emits structured output ✓ 7. Real verification on 36 sessions: session #35 was 478 min wall but only 48 min active (90% idle) — confirms metric correctly identifies AFK overrun ✓ NEGATIVE: empty DB returns 'No sessions to recompute', wall=0 → idle_pct shown as '-' ✓
- 2026-04-26T00:57:22Z [planning] — AC verified: 1. tausik session recompute parser in project_parser_session.py (--threshold/--limit/--json) ✓ 2. Table output # | wall | active | idle% | started_at + TOTAL row ✓ 3. Real verification: session #35 wall=482 active=48 (90% idle) — confirms metric correctly catches AFK overrun ✓ NEGATIVE: empty DB → 'No sessions to recompute', wall=0 → idle_pct '-' ✓
