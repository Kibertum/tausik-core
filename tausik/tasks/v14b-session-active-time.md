---
slug: v14b-session-active-time
title: "Session active-time counter — bounded sum of inter-tool-call deltas"
status: done
epic: null
story: null
complexity: medium
role: developer
stack: python
tier: light
call_budget: 25
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-04T12:03:48Z"
---

## Goal

session.duration counted as active time (sum of bounded inter-tool-call deltas, threshold 10min) instead of wall clock. Rule 9.2 (180-min limit) applies to active. /status shows active prominently, wall under --verbose.

## Acceptance Criteria

1. session.active_seconds field computed as sum(min(t[i+1]-t[i], 600s)) over consecutive tool_call timestamps in event log. 2. /status output shows `active: NNm / 180m`; wall_clock visible only with --verbose flag. 3. Rule 9.2 warning fires when active_seconds ≥ 180min (not wall). 4. Existing sessions: backfilled active_seconds via migration query OR field nullable (documented). 5. Tests: 3 scenarios — (a) short session no AFK; (b) session with 30-min gap (gap clipped to 10min in active sum); (c) session at active=180min (warning fires). 6. tausik_status MCP tool returns active_seconds in JSON. **Negative scenarios**: (a) session with NO tool-call events → active_seconds = 0 (not None, not NaN, not error); (b) wall-clock 200min but active 50min (long AFK gap) → no Rule 9.2 warning, active stays under threshold; (c) corrupt event timestamp (e.g. NULL or non-monotonic) → ignored without crashing the active calc, returns best-effort sum over valid pairs.

## Plan

[{"step": "Read scripts/service_session.py (or wherever session duration computed) to understand current wall-clock logic", "done": true}, {"step": "Add session.active_seconds field (DB migration if needed)", "done": true}, {"step": "Implement compute: sum(min(t[i+1]-t[i], 600s) for tool_calls in session)", "done": true}, {"step": "Update /status output: show 'active: NNm / 180m'; wall under --verbose", "done": true}, {"step": "Update Rule 9.2 warning to fire on active \u2265 180min", "done": true}, {"step": "Backfill: migration script computes active_seconds for closed sessions OR mark legacy sessions nullable", "done": true}, {"step": "Update tausik_status MCP tool to include active_seconds in JSON response", "done": true}, {"step": "Tests: 3 scenarios (no AFK, 30min gap clipped, active=180min triggers warning)", "done": true}, {"step": "docs/ru/agent-contract.md update on Rule 9.2 wording", "done": true}]

## Rollback

## Journal

- 2026-05-04T11:52:10Z [implementation] — Gap analysis: v1.3 already shipped gap-based active time with EXCLUDE semantics (gap≥threshold → 0 contribution), /status shows active prominently, MCP returns active_minutes, Rule 9.2 fires on active. AC demands CLIP semantics (gap≥threshold → contributes threshold itself; bounded inter-tool-call deltas) and sub-minute precision (active_seconds). Plan: (a) switch SQL CASE branch from THEN 0 to THEN ? clipping; (b) add compute_active_seconds returning seconds; (c) flip existing test_gap_above_threshold_excluded to clip expectation; (d) add 3 AC scenario + 3 negative tests; (e) expose active_seconds in MCP/CLI JSON; (f) refresh session-active-time.md + agent-contract.md wording from "excluded" to "bounded/clipped"; (g) bootstrap + bilingual CHANGELOG.
- 2026-05-04T12:01:32Z [implementation] — AC verified: 1. ✓ session.active_seconds computed via sum(min(Δ, idle_threshold_seconds)) in scripts/backend_session_metrics.py::compute_active_seconds (clip semantics, default threshold 600s/10min). compute_active_minutes is now a thin wrapper that rounds seconds to minutes. Both use the same SQL CASE clipping branch (THEN ? not THEN 0). 2. ✓ /status output shows `active Nm / Mm` prominently in scripts/project_cli.py::cmd_status; wall_clock surfaced under --verbose only (already shipped in v1.3, kept). 3. ✓ Rule 9.2 warning fires on active in scripts/service_session_metrics.py::session_overrun_warning (already shipped in v1.3, kept). With clip semantics, sessions with long AFK gaps now correctly contribute threshold-bounded active toward the 180-min limit instead of dropping to 0. 4. ✓ Existing sessions: computed on demand from events table, no migration needed; recompute_all_sessions retro-walks all sessions and now also returns active_seconds per row. 5. ✓ Tests: 24/24 in tests/test_backend_session_metrics.py pass. New TestComputeActiveSeconds class adds 9 cases covering AC scenarios + 3 negative scenarios (no events → 0, long AFK clipped → active stays low, non-monotonic timestamps best-effort). Existing test_gap_above_threshold_excluded renamed _clipped_not_excluded with assertion flipped 10→20 min. test_custom_threshold updated for clip behavior (threshold gap → threshold value, not 0). Full fast lane: 2752 passed, 7 skipped, 118 deselected (87s). 6. ✓ tausik_status MCP returns active_seconds in JSON: agents/{claude,cursor}/mcp/project/handlers.py::_handle_status sets data["active_seconds"] = svc.session_active_seconds(); scripts/tausik_utils.py::format_status_compact_json mirrors as `session_active_seconds`. 7. ✓ Negative scenarios covered explicitly: test_negative_a_no_events_returns_zero (returns int 0, not None/NaN), test_negative_b_long_afk_keeps_active_low (5min real + 195min clipped→10min = 15min active, well under 180), test_negative_c_corrupt_timestamps_best_effort (non-monotonic timestamps don't crash, returns sane non-negative int). 8. ✓ Bootstrap deployed (Skills 13, Scripts 101 copied; bootstrap drift "none"); .claude/mcp/project/server.py reloads on next IDE restart. 9. ✓ docs/{en,ru}/session-active-time.md rewritten around `Σ min(Δ, idle_threshold)` clip formula with v1.4 polish narrative; docs/ru/agent-contract.md Rule 9.2 row updated to describe bounded sum semantics; docs/{en,ru}/senar-compliance-matrix.md Rule 9.2 row updated. CHANGELOG.md + CHANGELOG.ru.md bilingual ### Changed entry under Unreleased Phase B with full root-cause story (exclude → clip semantic change, behavior-change disclosure, sub-minute precision exposure). 10. ✓ ruff clean on changed files. Doctor: 118m active / 787m wall (this session under clip semantics — note clip increased active vs old exclude reading, expected).</evidence> <parameter name="relevant_files">["scripts/backend_session_metrics.py", "scripts/service_session_metrics.py", "scripts/project_service.py", "scripts/tausik_utils.py", "agents/claude/mcp/project/handlers.py", "agents/cursor/mcp/project/handlers.py", "tests/test_backend_session_metrics.py", "docs/en/session-active-time.md", "docs/ru/session-active-time.md", "docs/ru/agent-contract.md", "docs/en/senar-compliance-matrix.md", "docs/ru/senar-compliance-matrix.md", "CHANGELOG.md", "CHANGELOG.ru.md"]
