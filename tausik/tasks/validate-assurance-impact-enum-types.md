---
slug: validate-assurance-impact-enum-types
title: "Reject non-scalar assurance impact enum values"
status: done
epic: null
story: null
complexity: simple
role: null
stack: null
tier: null
call_budget: null
defect_of: release-tausik-1-11-1
scope: "scripts/assurance_policy.py and aligned assurance/state/task/stack validation tests"
scope_exclude: "No change to valid assurance enum values or routing policy"
relevant_files:
  - "scripts/assurance_policy.py"
  - "tests/test_assurance_policy.py"
  - "tests/test_state_import.py"
  - "tests/test_task_context_package.py"
  - "tests/test_stack_registry.py"
scope_paths: []
scope_tools: []
assurance_profiles: []
assurance_impact: null
depends_on: []
completed_at: "2026-10-04T12:57:02Z"
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

Return structured validation errors for list, object, and other non-string assurance impact enum values.

## Acceptance Criteria

AC-1 validate_impact rejects non-string enum values without TypeError. AC-2 task normalization, stack validation, and state import surface actionable domain errors. AC-3 valid enum values remain accepted.

## Plan

## Rollback

Revert validator and boundary tests.

## Journal

- 2026-10-04T12:56:34Z [implementation] — Root cause (missing-validation): enum membership was evaluated before checking that JSON values were strings, so unhashable lists and objects raised TypeError instead of domain validation errors. Prevention: type-check enum values before membership and exercise policy, task, stack, and state-import boundaries.
- 2026-10-04T12:56:35Z [implementation] — Focused verification: 88 assurance policy, state import, task update, and stack registry tests passed; list/object/non-string enum values return structured errors.
- 2026-10-04T12:56:58Z [implementation] — ✓ AC-1 tests/test_assurance_policy.py::test_non_string_impact_enums_return_validation_errors covers list, object, integer, and boolean values without TypeError. ✓ AC-2 tests/test_task_context_package.py::test_task_update_rejects_non_string_assurance_impact_enum, tests/test_stack_registry.py::TestLoadBuiltin::test_non_string_assurance_impact_enum_is_skipped_with_error, and state-import parameter cases expose domain errors. ✓ AC-3 all existing valid assurance tests remain green. Domain: validation happens before persistence or import transaction application. Verify: verification_run #3486 passed 120 tests with 8 gates passed.
