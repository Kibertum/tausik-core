---
slug: correct-mixed-benchmark-invocation-coverage
title: "Correct mixed benchmark invocation coverage"
status: done
epic: null
story: null
complexity: medium
role: null
stack: null
tier: null
call_budget: null
defect_of: null
scope: "Benchmark cohort reviewer-invocation provenance aggregation and regression tests."
scope_exclude: "Review routing, snapshot persistence, and unrelated benchmark metrics."
relevant_files:
  - "scripts/benchmark_cohorts.py"
  - "scripts/benchmark_compare_support.py"
  - "tests/test_benchmark_cohorts.py"
scope_paths: []
scope_tools: []
assurance_profiles: []
assurance_impact: null
depends_on: []
completed_at: "2026-10-04T13:42:16Z"
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

Report per-task review-invocation provenance coverage accurately for mixed modern and legacy cohorts.

## Acceptance Criteria

AC-1: Mixed modern and legacy cohorts report the number of tasks with known invocation provenance over the total task count. AC-2 negative: unknown legacy provenance keeps aggregate reviewer invocations unknown and does not erase coverage from modern tasks. AC-3: focused tests pass.

## Plan

## Rollback

Revert per-task invocation coverage aggregation.

## Journal

- 2026-10-04T13:41:54Z [implementation] — AC-1: review invocation coverage now counts each attributable task whose full review history has route metadata and measured invocation values. AC-2: ✓ tests/test_benchmark_cohorts.py::test_mixed_review_provenance_keeps_per_task_invocation_coverage reports 1/2 while aggregate reviewer_invocations stays unknown. AC-3: ✓ 33 focused cohort/compare tests passed. Domain: the coverage numerator no longer discards known modern evidence because another task is legacy.
- 2026-10-04T13:42:12Z [implementation] — AC-1: ✓ scripts/benchmark_cohorts.py counts known invocation provenance per task. AC-2: ✓ mixed modern/legacy regression reports 1/2 coverage while aggregate invocations remain unknown. AC-3: ✓ verify #3506 passed 33 tests, 0 failed across 2 mapped files; 8 gates passed, hadolint skipped as not applicable. Domain: mixed cohorts retain honest partial provenance coverage.
