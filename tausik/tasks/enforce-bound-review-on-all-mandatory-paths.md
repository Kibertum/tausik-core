---
slug: enforce-bound-review-on-all-mandatory-paths
title: "Enforce bound review evidence on every mandatory review path"
status: done
epic: null
story: null
complexity: medium
role: null
stack: null
tier: null
call_budget: null
defect_of: release-tausik-1-11-1
scope: "scripts/risk_l3_trigger.py, scripts/service_review_gate.py, scripts/service_task_done.py and directly aligned review/closure tests"
scope_exclude: "No review policy downgrade, unrelated assurance routing, or release publication"
relevant_files:
  - "scripts/risk_l3_trigger.py"
  - "scripts/service_task_done.py"
  - "tests/test_risk_l3_trigger.py"
  - "tests/test_review_routing.py"
scope_paths: []
scope_tools: []
assurance_profiles: []
assurance_impact: null
depends_on: []
completed_at: "2026-10-04T12:47:57Z"
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

Make measured-risk and assurance closure checks reject missing, legacy, or stale review bindings on every mandatory review route.

## Acceptance Criteria

AC-1 Changing task contract or relevant files after an L3 review makes both measured-risk and assurance closure checks reject it. AC-2 current bound reviews still satisfy their required route. AC-3 integrated closure regressions cover tasks without assurance declarations. Negative: no finding-count-only acceptance remains.

## Plan

## Rollback

Revert the review-gate service and regression tests.

## Journal

- 2026-10-04T12:46:10Z [implementation] — Focused verification: tests/test_risk_l3_trigger.py plus tests/test_review_routing.py passed 56 tests; integrated regression proves a goal change after bound L3 review blocks closure for a task with no assurance declarations.
- 2026-10-04T12:46:10Z [implementation] — Root cause (missing-validation): the measured-risk L3 gate accepted the latest review by finding counts only and never checked the reviewed-state fingerprint, while its exception path failed open. Prevention: route every mandatory L3 decision through canonical review_record_blockers and fail closed when review validation cannot execute.
- 2026-10-04T12:47:43Z [implementation] — ✓ AC-1 task-contract changes invalidate bound L3 evidence in measured-risk and canonical review validation. ✓ AC-2 a current external L3 with recognized distinct model families still satisfies the route. ✓ AC-3 integrated closure regression covers a task without assurance declarations. ✓ Negative: finding counts alone no longer satisfy mandatory L3 and validation errors fail closed. Domain: closure uses the database-derived project root and the same persisted fingerprint as review recording.
- 2026-10-04T12:47:56Z [implementation] — ✓ AC-1 task-contract changes invalidate bound L3 evidence in measured-risk and canonical review validation. ✓ AC-2 a current external L3 with recognized distinct model families still satisfies the route. ✓ AC-3 integrated closure regression covers a task without assurance declarations. ✓ Negative: finding counts alone no longer satisfy mandatory L3 and validation errors fail closed. Domain: closure uses the database-derived project root and the same persisted fingerprint as review recording.
