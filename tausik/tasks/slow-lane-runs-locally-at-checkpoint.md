---
slug: slow-lane-runs-locally-at-checkpoint
title: "Slow lane runs nowhere while push is forbidden: run it locally at checkpoint"
status: done
epic: release-110-deferred-from-19
story: deferred-110-audit-hygiene
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "tests/conftest.py"
  - "tests/test_handoff_slow_lane.py"
  - "scripts/handoff_generate.py"
  - "scripts/service_session.py"
  - "harness/skills/checkpoint/SKILL.md"
  - "changelog.d/slow-lane-runs-locally-at-checkpoint.md"
scope_paths:
  - "harness/"
  - "scripts/"
  - "docs/"
  - "changelog.d/"
  - "tests/"
scope_tools: []
depends_on: []
completed_at: "2026-09-29T21:07:15Z"
resolution: null
resolution_reason: null
tracker_refs: []
started_model_id: claude-opus-5
started_model_version: null
done_model_id: claude-opus-5
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
---

## Goal

Owner instruction session #279. pytest -q deselects -m slow; CI runs the full lane but push is forbidden until release (decision #400), so two slow tests stayed red through session #278 unseen. Checkpoint must run the slow lane locally and put its verdict into the handoff.

## Acceptance Criteria

AC-1 /checkpoint runs pytest -q -m slow and records passed/failed/deselected in the handoff. AC-2 NEGATIVE: a red or not-run slow lane is a handoff warning, never silence. AC-3 The step costs one call, not a separate ceremony.

## Plan

## Rollback

git revert

## Journal

- 2026-09-29T21:05:15Z [implementation] — Done: conftest writes .tausik/slow_lane.json on a whole-tree -m slow / -m '' run (partial runs ignored); handoff_generate.slow_lane() adds slow_lane: green / RED n failed / NOT RUN this session / UNREADABLE; service passes the DB's .tausik dir; checkpoint SKILL step runs the lane in background where the record exists. Evidence: real run wrote {ran_at, markexpr slow, exit_status 1, passed 141, failed 1}; tests/test_handoff_slow_lane.py 8 passed incl. end-to-end session_handoff. AC verified: 1. checkpoint step + record 2. NOT RUN/RED/UNREADABLE said in words, tested 3. one background call.
- 2026-09-29T21:07:14Z [implementation] — NO-DEAD-END: the red run was bootstrap_drift (deployed profiles not refreshed after editing scripts/), fixed by bootstrap --ide all; not a wrong approach.
- 2026-09-29T21:07:25Z [done] — AC-1: ✓ real run wrote .tausik/slow_lane.json; checkpoint SKILL step. AC-2: ✓ tests/test_handoff_slow_lane.py::test_the_lane_state_is_said_in_words, ::test_an_unreadable_record_is_said_not_swallowed, ::test_the_saved_handoff_carries_the_lane_from_the_db_directory. AC-3: ✓ one background call; verify_run green after bootstrap.
