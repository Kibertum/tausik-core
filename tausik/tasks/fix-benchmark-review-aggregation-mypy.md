---
slug: fix-benchmark-review-aggregation-mypy
title: "Fix benchmark review aggregation type contract"
status: done
epic: null
story: null
complexity: simple
role: null
stack: null
tier: null
call_budget: null
defect_of: release-tausik-1-11-1
scope: "scripts/benchmark_compare_support.py and aligned benchmark tests"
scope_exclude: "No metric or cohort semantic changes"
relevant_files:
  - "scripts/benchmark_compare_support.py"
  - "scripts/benchmark_compare.py"
  - "scripts/benchmark_cohorts.py"
  - "tests/test_benchmark_compare.py"
  - "tests/test_benchmark_cohorts.py"
  - "tests/test_mypy_clean.py"
  - "tests/test_mypy_gate_scope.py"
scope_paths: []
scope_tools: []
assurance_profiles: []
assurance_impact: null
depends_on: []
completed_at: "2026-10-04T13:11:39Z"
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

Make the shared provenance-aware reviewer invocation aggregator pass the repository mypy contract without changing semantics.

## Acceptance Criteria

AC-1 mypy passes for all benchmark modules. AC-2 legacy unknown and modern zero behavior stays green. Negative: empty, missing-route, or missing-count input still returns unknown.

## Plan

## Rollback

Revert the helper typing refactor and aligned tests.

## Journal

- 2026-10-04T13:11:15Z [implementation] — Focused verification: mypy reports no issues in the three benchmark modules; 43 benchmark and mypy-gate tests passed.
- 2026-10-04T13:11:15Z [implementation] — Root cause (integration-mismatch): the shared helper accepted invariant list[Mapping] and summed an Any-or-None generator that mypy could not narrow, although both callers provide lists of concrete dictionaries. Prevention: accept covariant Iterable[Mapping] and narrow each optional value before conversion.
- 2026-10-04T13:11:35Z [implementation] — ✓ AC-1 mypy reports no issues in benchmark_compare_support.py, benchmark_compare.py, or benchmark_cohorts.py. ✓ AC-2 31 benchmark behavior tests retain legacy-unknown and modern-zero semantics. ✓ Negative: the helper returns None before conversion for empty input, missing route metadata, or missing counts. Domain: Iterable[Mapping] matches both report callers without unsafe casts. Verify: verification_run #3494 passed 43 tests with 8 gates passed.
