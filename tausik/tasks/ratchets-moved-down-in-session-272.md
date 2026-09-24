---
slug: ratchets-moved-down-in-session-272
title: "Ratchets moved down in session #272: lower test_dedupe and the ruff_format legacy list"
status: done
epic: release-110-deferred-from-19
story: release110-verification-is-cheap
complexity: simple
role: developer
stack: null
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "tausik/gates.json"
  - "tests/test_gate_test_dedupe.py"
  - "tests/test_gate_ruff_format.py"
scope_paths:
  - "tausik/gates.json"
scope_tools: []
depends_on: []
completed_at: "2026-09-24T06:31:37Z"
---

## Goal

The two ratchets that the session's changes pushed below their committed baselines are lowered to what was achieved, as their own tests require.

## Acceptance Criteria

1. tausik/gates.json test_dedupe baseline equals the measurement (287 groups / 679 tests). 2. tests/test_user_prompt_submit_hook.py leaves ruff_format.legacy_unformatted because it is formatted now. 3. NEGATIVE: both ratchet tests go green without raising anything — the lists only shrink.

## Plan

## Rollback

git revert

## Journal

- 2026-09-24T06:31:09Z [implementation] — AC-1: ✓ tests/test_gate_test_dedupe.py::test_the_baseline_only_ratchets_down — baseline 288/682 -> 287/679, the measurement of the full run of session #272.
- 2026-09-24T06:31:10Z [implementation] — AC-2: ✓ tests/test_gate_ruff_format.py::test_the_legacy_list_only_shrinks — tests/test_user_prompt_submit_hook.py removed from the frozen list (formatted by the rag-nudge task).
- 2026-09-24T06:31:10Z [implementation] — AC-3: ✓ tests/test_gate_test_dedupe.py::test_growth_is_red_and_says_where — negative, both ratchets green with nothing raised.
