---
slug: bind-assurance-stack-registry-to-service-project
title: "Resolve assurance stack declarations from the service project"
status: done
epic: null
story: null
complexity: medium
role: null
stack: null
tier: null
call_budget: null
defect_of: release-tausik-1-11-1
scope: "scripts/stack_registry.py, scripts/task_context_package.py, scripts/service_review_gate.py and directly aligned tests"
scope_exclude: "No changes to stack schema semantics or unrelated registry consumers"
relevant_files:
  - "scripts/stack_registry.py"
  - "scripts/task_context_package.py"
  - "scripts/service_review_gate.py"
  - "tests/test_stack_registry.py"
  - "tests/test_task_context_package.py"
  - "tests/test_review_routing.py"
scope_paths: []
scope_tools: []
assurance_profiles: []
assurance_impact: null
depends_on: []
completed_at: "2026-10-04T12:54:40Z"
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

Load stack assurance defaults from the target service project instead of ambient cwd in task packaging and closure enforcement.

## Acceptance Criteria

AC-1 task package and closure gate use the target service project stack registry. AC-2 conflicting cwd and target project stack defaults select the target. AC-3 security or governance floors cannot disappear for tasks without task-level declarations. Negative: no process-global cwd registry controls another project.

## Plan

## Rollback

Revert project-scoped registry resolution and tests.

## Journal

- 2026-10-04T12:54:12Z [implementation] — Focused verification: ruff passed and 78 stack registry, context package, and closure routing tests passed; target-project governance floor remains L3 when cwd points at a different project.
- 2026-10-04T12:54:12Z [implementation] — Root cause (integration-mismatch): assurance consumers reused the process-global stack registry, whose user overrides were loaded once from ambient cwd rather than from the backend-bound service project. Prevention: construct the assurance registry from service.tausik_dir() at each project boundary and test conflicting cwd/target projects.
- 2026-10-04T12:54:37Z [implementation] — ✓ AC-1 tests/test_task_context_package.py::test_assurance_uses_target_project_stack_override_not_ambient_cwd proves package routing uses the service project. ✓ AC-2 tests/test_stack_registry.py::test_project_registry_loads_only_the_explicit_projects_overrides proves conflicting cwd is ignored. ✓ AC-3 tests/test_review_routing.py::test_qg2_uses_target_project_stack_floor_when_cwd_is_another_project proves closure keeps the target governance L3 floor. ✓ Negative: process-global cwd registry is absent from both assurance consumers. Verify: verification_run #3484 passed 117 tests with 8 gates passed.
- 2026-10-04T12:54:53Z [done] — Domain: an explicit service DB path now resolves both config.json and .tausik/stacks from the same project root; built-in declarations still come from the installed framework. Knowledge: this extends existing memory #906 from review config to stack declarations, so no duplicate memory was added.
