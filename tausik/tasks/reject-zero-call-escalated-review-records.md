---
slug: reject-zero-call-escalated-review-records
title: "Reject zero-call escalated review records"
status: done
epic: null
story: null
complexity: medium
role: null
stack: null
tier: null
call_budget: null
defect_of: null
scope: "Review route validation and its behavioral regressions."
scope_exclude: "Risk configuration, update cache, benchmark aggregation, and documentation."
relevant_files:
  - "scripts/review_routing.py"
  - "tests/test_review_routing.py"
  - "tests/test_risk_l3_trigger.py"
scope_paths: []
scope_tools: []
assurance_profiles: []
assurance_impact: null
depends_on: []
completed_at: "2026-10-04T13:34:32Z"
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

Ensure every recorded L2/L3 review proves the invocation depth required by its actual recorded level and mandatory closure cannot accept a stronger label with weaker execution.

## Acceptance Criteria

Recording and closure reject L2/L3 records whose reviewer invocation count is below the actual level requirement; an L1-route/L3-record zero-call regression fails closed; focused tests pass.

## Plan

## Rollback

Revert the review-routing validation and its tests.

## Journal

- 2026-10-04T13:33:36Z [implementation] — Implemented actual-level invocation floor: L2/L3 records require at least one reviewer invocation even when their stored route is L1. Added direct L2/L3 and bound closure regressions. Focused result: 60 passed.
- 2026-10-04T13:34:28Z [implementation] — AC verified: actual recorded L2/L3 levels enforce at least one reviewer invocation even when stored route is L1; direct and closure regressions pass. Verify #3496: 60 passed, 0 failed across 2 mapped test files; 8 gates passed, hadolint skipped as not applicable.
- 2026-10-04T13:34:40Z [done] — AC-1: ✓ tests/test_review_routing.py::test_stronger_record_cannot_borrow_zero_invocations_from_l1_route and ::test_bound_l3_record_with_l1_route_and_zero_invocations_fails_closed; verify #3496 passed 60 tests. Domain: an L3 label can no longer substitute for a real external reviewer call.
