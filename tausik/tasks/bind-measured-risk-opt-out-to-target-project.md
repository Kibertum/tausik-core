---
slug: bind-measured-risk-opt-out-to-target-project
title: "Bind measured-risk opt-out to target project"
status: done
epic: null
story: null
complexity: medium
role: null
stack: null
tier: null
call_budget: null
defect_of: null
scope: "Measured-risk L3 configuration lookup and task-done integration."
scope_exclude: "Review record validation, benchmark aggregation, bootstrap generation, and update cache."
relevant_files:
  - "scripts/risk_l3_trigger.py"
  - "scripts/service_task_done.py"
  - "tests/test_risk_l3_trigger.py"
  - "tests/test_bypass_telemetry.py"
scope_paths: []
scope_tools: []
assurance_profiles: []
assurance_impact: null
depends_on: []
completed_at: "2026-10-04T13:38:16Z"
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

Make the mandatory measured-risk L3 gate read configuration only from the service target project.

## Acceptance Criteria

AC-1: The gate derives configuration from the target service project or explicit project root. AC-2 negative: an ambient project with l3_block_on_high=false cannot bypass a target project that requires L3. AC-3: focused tests pass.

## Plan

## Rollback

Revert the target-project configuration lookup and regressions.

## Journal

- 2026-10-04T13:36:19Z [implementation] — AC-1: check_l3_required resolves .tausik from explicit target root or database connection. AC-2: ✓ tests/test_risk_l3_trigger.py::TestTaskDoneIntegration::test_task_done_uses_target_project_for_l3_opt_out proves an ambient opt-out cannot bypass a target requiring L3. AC-3: ✓ 27 focused tests passed. Domain: the service handle now controls the mandatory closure policy.
- 2026-10-04T13:38:12Z [implementation] — AC-1: ✓ scripts/risk_l3_trigger.py resolves configuration from the explicit service project or connection DB. AC-2: ✓ tests/test_risk_l3_trigger.py::TestTaskDoneIntegration::test_task_done_uses_target_project_for_l3_opt_out rejects an ambient opt-out bypass. AC-3: ✓ verify #3500 passed 593 tests, 0 failed across 27 mapped files; 8 gates passed, hadolint skipped as not applicable. Domain: task closure policy follows the target service handle.
