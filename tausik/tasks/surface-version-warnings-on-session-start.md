---
slug: surface-version-warnings-on-session-start
title: "Surface version-check warnings on successful session start"
status: done
epic: null
story: null
complexity: simple
role: null
stack: null
tier: null
call_budget: null
defect_of: release-tausik-1-11-1
scope: "scripts/hooks/session_start.py and aligned session-start hook tests"
scope_exclude: "No change to release-check network policy or session creation semantics"
relevant_files:
  - "scripts/hooks/session_start.py"
  - "tests/test_session_host_binding.py"
  - "tests/test_session_open_handler.py"
  - "tests/test_update_check.py"
scope_paths: []
scope_tools: []
assurance_profiles: []
assurance_impact: null
depends_on: []
completed_at: "2026-10-04T13:00:49Z"
resolution: null
resolution_reason: null
tracker_refs: []
started_model_id: null
started_model_version: null
done_model_id: null
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
---

## Goal

Expose unverified-version stderr warnings to the host even when session start otherwise succeeds.

## Acceptance Criteria

AC-1 offline and disabled release checks place the unverified-version warning in additionalContext. AC-2 clean successful starts remain concise. AC-3 session creation still succeeds. Negative: a successful start with stderr must not discard that warning or suppress normal project context.

## Plan

## Rollback

Revert session hook warning propagation and tests.

## Journal

- 2026-10-04T13:00:07Z [implementation] — Root cause (logic-error): _open_host_session returned None for every zero exit code, discarding stderr even though session start intentionally emits release-check uncertainty there. Prevention: preserve successful stderr as a typed session notice and merge it with normal additionalContext rather than treating it as a refusal.
- 2026-10-04T13:00:08Z [implementation] — Focused verification: ruff passed and 72 session binding, session-open, and update-check tests passed; offline/disabled warnings are surfaced while normal context and successful session creation remain.
- 2026-10-04T13:00:45Z [implementation] — ✓ AC-1 tests/test_session_host_binding.py::TestTheHooks::test_successful_session_start_surfaces_version_warning covers offline and disabled warning forms. ✓ AC-2 tests/test_session_host_binding.py::TestTheHooks::test_session_start_hook_opens_the_host_session keeps clean success as None. ✓ AC-3 all session-open integration tests remain green. ✓ Negative: test_success_warning_is_combined_with_normal_additional_context proves stderr survives without suppressing project context. Domain: the hook still exits zero and distinguishes warnings from session refusals. Verify: verification_run #3490 passed 439 tests with 8 gates passed.
