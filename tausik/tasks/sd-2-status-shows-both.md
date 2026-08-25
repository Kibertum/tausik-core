---
slug: sd-2-status-shows-both
title: "tausik status: show \"X min active / Y wall clock\""
status: done
epic: v13-mcp-and-discipline
story: session-duration-fix
complexity: null
role: developer
stack: python
tier: trivial
call_budget: 10
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/project_cli.py"
  - "scripts/project_service.py"
  - "scripts/service_session_metrics.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-26T00:57:22Z"
---

## Goal

Update `tausik status` CLI output to show both active minutes and wall-clock for current session. Format: "Session: #36 (95 min active / 5h12m wall)".

## Acceptance Criteria

1. cmd_status prints 'Session: #N (X min active / Y min wall)'. 2. session_active_minutes() and session_wall_minutes() exposed on ProjectService. 3. Idle pct shown when wall>0 and active<wall. NEGATIVE: no /0 division when wall=0.

## Plan

## Rollback

## Journal

- 2026-04-26T00:52:34Z [planning] — AC verified: 1. cmd_status (project_cli.py:58) prints 'Session: #N (X min active / Y min wall, Z% idle)' ✓ 2. session_active_minutes() and session_wall_minutes() added to ProjectService ✓ 3. Real verification: tausik status output: 'Session: #36 (4 min active / 100 min wall, 96% idle)' ✓ NEGATIVE: idle_pct only shown when wall>0 and active<wall (avoids /0 and >100%) ✓
- 2026-04-26T00:57:22Z [planning] — AC verified: 1. cmd_status prints active+wall+idle% (verified: 'Session: #36 (4 min active / 100 min wall, 96% idle)') ✓ 2. Methods on ProjectService thin-wrap service_session_metrics helpers ✓ 3. Idle pct guarded by wall>0 and active<wall ✓ NEGATIVE: 0% wall doesn't crash (idle_pct empty string) ✓
