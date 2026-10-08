---
slug: load-review-floor-configuration-from-the-service
title: "Load review floor configuration from the service project"
status: done
epic: null
story: null
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: route-ship-by-residual-assurance
scope: "scripts/task_context_package.py and aligned review-routing/task-package tests."
scope_exclude: "No changes to review route rules, configuration format, or unrelated context package fields."
relevant_files:
  - "scripts/task_context_package.py"
  - "scripts/service_review_gate.py"
  - "tests/test_task_context_package.py"
scope_paths: []
scope_tools: []
assurance_profiles: []
assurance_impact: null
depends_on: []
completed_at: "2026-10-04T12:10:22Z"
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

Ensure MCP and multi-project review routing reads extreme_hard_floor from the project represented by the service, never ambient cwd.

## Acceptance Criteria

AC-1 task package routing loads configuration from svc.tausik_dir(). AC-2 a test with conflicting cwd and service-project configs preserves the target project's hard floor. Negative: ambient cwd cannot weaken the target route.

## Plan

## Rollback

Revert the focused fix commit; retain the release block until a replacement fix passes review and verification.

## Journal

- 2026-10-04T12:10:10Z [implementation] — Root cause (config-error): task context built the review route with load_config() and therefore ambient cwd instead of the service-owned .tausik directory. Prevention: every project-scoped read accepts the service handle explicitly; conflicting-cwd regression holds the boundary.
- 2026-10-04T12:10:17Z [implementation] — AC verified: AC-1 ✓ _review_route now receives svc and calls load_config(svc.tausik_dir()). AC-2 ✓ conflicting service/ambient configs preserve L3-deep with seven invocations; focused package/routing tests 47 passed. Negative ✓ ambient extreme_hard_floor=false cannot weaken target true. Scoped critical verify #3472: 30 passed over 2/659 files.
- 2026-10-04T12:10:18Z [implementation] — NO-DEAD-END: the initial focused red exposed the missing svc parameter and invalid fixture enum values directly; both were corrected without abandoning an approach.
