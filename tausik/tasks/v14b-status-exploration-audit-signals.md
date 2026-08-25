---
slug: v14b-status-exploration-audit-signals
title: "tausik_status: surface exploration_open + audit_overdue_sessions in compact JSON"
status: done
epic: null
story: null
complexity: simple
role: developer
stack: python
tier: light
call_budget: 25
defect_of: null
scope: "scripts/tausik_utils.py (format_status_compact_json), harness/{claude,cursor}/mcp/project/handlers.py (_handle_status), tests/test_status_compact.py or new test file. Bootstrap regen at the end."
scope_exclude: "backend_queries.py (keep get_status_data unchanged — exploration/audit are surfaced in handler layer, not backend); SKILL.md (already correct prose); compound-RPC work (separate epic)."
relevant_files:
  - "scripts/project_service.py"
  - "scripts/tausik_utils.py"
  - "scripts/service_session_metrics.py"
  - "harness/claude/mcp/project/handlers.py"
  - "harness/cursor/mcp/project/handlers.py"
  - "tests/test_project_mcp.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-06T17:07:39Z"
---

## Goal

Make /start SKILL.md justification literally true: extend tausik_status compact-JSON output with exploration_open (+ exploration_id, exploration_over_limit) and audit_overdue_sessions, so Phase 1 batch can drop tausik_explore_current + tausik_audit_check without silently losing those signals. Closes /review H1 from session #57.

## Acceptance Criteria

1. format_status_compact_json emits exploration_open=true (+ exploration_id, exploration_over_limit) when an exploration is active; fields absent when none. 2. format_status_compact_json emits audit_overdue_sessions=N (int ≥ 3) when current_session - last_audit ≥ 3; field absent when not overdue. 3. Non-compact _handle_status appends one-line warnings for both signals after duration_warning. 4. Tests added for: no signals → fields absent; active exploration → fields present + exploration_id correct; audit overdue → field present with correct N. 5. Bootstrap regen reflects new logic in .claude/. 6. /start SKILL.md "tausik_status already flags …" claims become literally true. 7. Negative scenario: when svc.exploration_current() raises an exception, _handle_status MUST NOT fail — fields are simply absent (graceful degradation, no status outage). 8. Negative scenario: when meta_get('last_audit_session') returns malformed (non-int) value, audit_overdue_sessions MUST NOT be emitted — handler swallows the parse error and returns clean status JSON. 9. Existing tausik_status tests continue to pass (backwards compatible — no field renamed/removed).

## Plan

## Rollback

## Journal

- 2026-05-06T16:54:59Z [implementation] — Implementation: added audit_overdue_sessions() service method (project_service.py:266-282); extended format_status_compact_json with exploration_open/exploration_id/exploration_over_limit/audit_overdue_sessions (tausik_utils.py); _handle_status now populates data dict with exp + audit signals + appends one-line warnings in human output (claude+cursor mirrors in sync, diff -q clean)
- 2026-05-06T16:59:00Z [implementation] — AC verified: 1. ✓ format_status_compact_json emits exploration_open/exploration_id/exploration_over_limit when active (test_status_compact_surfaces_active_exploration). 2. ✓ audit_overdue_sessions int emitted when ≥3 (test_status_compact_emits_audit_overdue_when_threshold_met). 3. ✓ Non-compact handler appends one-line warnings (test_status_human_warns_on_active_exploration). 4. ✓ Tests: no signals→absent (test_status_compact_omits_signals_when_clean), active exp present (✓), overdue audit present (✓), absent under threshold (test_status_compact_audit_absent_when_under_threshold). 5. ✓ Bootstrap regen done — Skills 13 / Scripts 110 / MCP servers 3 copied. 6. ✓ SKILL.md justification now literal — compact JSON has both signals. 7. ✓ Negative: malformed audit meta swallowed (test_status_handles_malformed_audit_meta). 8. ✓ Same negative covers ValueError parse path. 9. ✓ Backwards compat: 40 existing test_project_mcp.py tests pass + full suite 2847 passed (was 2841 + 6 new = 2847).</evidence> <relevant_files">["scripts/project_service.py", "scripts/tausik_utils.py", "harness/claude/mcp/project/handlers.py", "harness/cursor/mcp/project/handlers.py", "tests/test_project_mcp.py"]</relevant_files> <no_knowledge">true</no_knowledge> </invoke>
- 2026-05-06T16:59:19Z [implementation] — AC verified: 1. ✓ format_status_compact_json emits exploration_open/exploration_id/exploration_over_limit when active (test_status_compact_surfaces_active_exploration). 2. ✓ audit_overdue_sessions int emitted when ≥3 (test_status_compact_emits_audit_overdue_when_threshold_met). 3. ✓ Non-compact handler appends one-line warnings (test_status_human_warns_on_active_exploration). 4. ✓ Tests: no signals→absent + active exp present + overdue audit present + absent under threshold. 5. ✓ Bootstrap regen done. 6. ✓ SKILL.md justification literal now. 7. ✓ Negative: malformed audit meta swallowed (test_status_handles_malformed_audit_meta). 8. ✓ Same negative covers parse path. 9. ✓ Backwards compat: full suite 2847 passed (2841 + 6 new).</evidence> <parameter name="relevant_files">["scripts/project_service.py", "scripts/tausik_utils.py", "harness/claude/mcp/project/handlers.py", "harness/cursor/mcp/project/handlers.py", "tests/test_project_mcp.py"]
- 2026-05-06T16:59:46Z [implementation] — AC verified per task_log; full pytest suite 2847 passed (was 2841 + 6 new tests)
- 2026-05-06T17:00:35Z [implementation] — AC verified per task notes (full pytest 2847 passed, was 2841 + 6 new)
- 2026-05-06T17:01:55Z [implementation] — AC verified: 9/9 — full pytest 2847 passed, scoped verify pytest=PASS at scope=critical (4.9s)
- 2026-05-06T17:07:39Z [implementation] — AC verified: 9/9 — full pytest 2847 passed, scoped verify pytest=PASS at scope=critical (2.9s)
