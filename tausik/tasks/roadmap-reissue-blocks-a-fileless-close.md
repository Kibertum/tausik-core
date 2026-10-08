---
slug: roadmap-reissue-blocks-a-fileless-close
title: "A status change reissues ROADMAP.md, and the reissued file then refuses a --no-file-changes close"
status: done
epic: release-110-deferred-from-19
story: release110-owner-priorities
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/state_triggers.py"
  - "scripts/gate_verify_first.py"
  - "tests/test_roadmap_reissue_fileless_close.py"
  - "changelog.d/roadmap-reissue-blocks-a-fileless-close.md"
scope_paths:
  - "scripts/"
  - "tests/"
  - "changelog.d/"
scope_tools: []
depends_on: []
completed_at: "2026-09-29T22:42:07Z"
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

Session #279: task unblock rewrote ROADMAP.md (counters moved), and task done --no-file-changes then refused because git saw ROADMAP.md modified. The fileless-close exclusion covers tausik/{tasks,...} projections but not the generated ROADMAP.md, so any status change before a fileless close forces a commit.

## Acceptance Criteria

AC-1 A ROADMAP.md change produced only by the generator does not refuse a fileless close. AC-2 NEGATIVE: a hand edit to ROADMAP.md still refuses it. AC-3 Test covers both.

## Plan

## Rollback

git revert

## Journal

- 2026-09-29T22:38:39Z [implementation] — AC-1: ✓ tests/test_roadmap_reissue_fileless_close.py::test_the_generators_own_output_is_excused (state_triggers.roadmap_is_generated used in gate_verify_first._enforce_no_file_changes). AC-2 Negative: ✓ ::test_a_hand_edit_is_still_work and ::test_a_file_without_the_generator_mark_is_never_excused. AC-3: ✓ both covered; tests/test_fileless_close.py still green (32 passed together).
- 2026-09-29T22:39:13Z [implementation] — NO-DEAD-END: the red run was the filesize cap (state_triggers.py 502 lines); the helper moved to gate_verify_first.py (493), its only caller.
