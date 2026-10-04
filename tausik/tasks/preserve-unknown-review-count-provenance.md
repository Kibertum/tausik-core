---
slug: preserve-unknown-review-count-provenance
title: "Preserve unknown provenance in benchmark review counts"
status: done
epic: null
story: null
complexity: simple
role: null
stack: null
tier: null
call_budget: null
defect_of: release-tausik-1-11-1
scope: "scripts/benchmark_compare.py, shared benchmark aggregation helper if needed, and aligned benchmark tests"
scope_exclude: "No cohort membership or release savings claim changes"
relevant_files:
  - "scripts/benchmark_compare.py"
  - "scripts/benchmark_cohorts.py"
  - "scripts/benchmark_compare_support.py"
  - "tests/test_benchmark_compare.py"
  - "tests/test_benchmark_cohorts.py"
scope_paths: []
scope_tools: []
assurance_profiles: []
assurance_impact: null
depends_on: []
completed_at: "2026-10-04T12:58:43Z"
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

Keep migrated legacy reviewer invocation counts unknown rather than measuring them as zero in benchmark comparison.

## Acceptance Criteria

AC-1 route_json NULL legacy reviews do not contribute measured zero reviewer invocations. AC-2 comparison and cohort inventory share provenance semantics. AC-3 measured modern zeros remain zero. Negative: mixed measured and legacy rows report unknown rather than a partial total.

## Plan

## Rollback

Revert comparison aggregation and aligned tests.

## Journal

- 2026-10-04T12:58:19Z [implementation] — Root cause (integration-mismatch): cohort inventory treated route_json NULL as unknown provenance, but comparison reused a generic complete sum over migrated reviewer_invocations defaults and therefore counted legacy zero as measured. Prevention: share one provenance-aware review-count aggregator across both reports.
- 2026-10-04T12:58:20Z [implementation] — Focused verification: ruff passed and 31 benchmark comparison/cohort tests passed; mixed legacy and modern zero reports unknown while all-modern measured zero remains zero.
- 2026-10-04T12:58:39Z [implementation] — ✓ AC-1 tests/test_benchmark_compare.py::test_legacy_review_zero_stays_unknown_while_modern_zero_is_measured proves route_json NULL stays unknown. ✓ AC-2 benchmark_compare and benchmark_cohorts call measured_reviewer_invocations from benchmark_compare_support. ✓ AC-3 the same regression proves modern zero remains measured zero. ✓ Negative: mixed modern/legacy rows yield None, not a partial sum. Domain: migrated database defaults no longer fabricate measured reviewer work. Verify: verification_run #3488 passed 31 tests with 8 gates passed.
