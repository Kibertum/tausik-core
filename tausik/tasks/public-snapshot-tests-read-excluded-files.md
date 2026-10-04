---
slug: public-snapshot-tests-read-excluded-files
title: "GitHub is red on 1.10.0: four tests read files the public snapshot excludes"
status: done
epic: release-110-deferred-from-19
story: release110-owner-priorities
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "tests/test_publication_lines.py aligns the historical leak ratchet with scripts/publication_snapshot.py; focused public-snapshot tests and a temporary filtered working-tree checkout verify behavior."
scope_exclude: "No production publication semantics, exclusion list, tracker mutation, commit, push, tag, release, paid/synthetic model run or broad unrelated test refactor."
relevant_files:
  - "tests/test_publication_lines.py"
  - "scripts/benchmark_compare_support.py"
  - "scripts/benchmark_compare.py"
  - "scripts/benchmark_cohorts.py"
  - "scripts/backend_crud.py"
  - "scripts/service_review_gate.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths:
  - "tests/test_publication_lines.py"
  - "scripts/benchmark_compare_support.py"
  - "scripts/benchmark_compare.py"
  - "scripts/benchmark_cohorts.py"
  - "scripts/backend_crud.py"
  - "scripts/service_review_gate.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
assurance_profiles: []
assurance_impact: null
depends_on: []
completed_at: "2026-10-04T10:39:56Z"
resolution: null
resolution_reason: null
tracker_refs: []
started_model_id: claude-opus-5
started_model_version: null
done_model_id: null
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
---

## Goal

Make public-boundary tests evaluate the same filtered tree that publication ships, while keeping development-line and planted-violation checks fail-closed.

## Acceptance Criteria

AC-1 Public-boundary scans derive their file set from EXCLUDED_FROM_PUBLIC_SNAPSHOT and apply the same AGENTS.md/CLAUDE.md dynamic-block sanitization as production. AC-2 The original four 1.10.0 snapshot regressions still pass or skip with a named reason, and mypy remains clean when development-only ci_lane_dev.py is absent. AC-3 Negative: an excluded-only violation is ignored, but the same violation in a kept public file is detected; development-line controls still execute. AC-4 A locally materialized filtered working-tree snapshot passes the focused public test lane before 1.11.1 publication. AC-5 Focused tests, pytest dedupe audit and tausik_verify pass with full AC, Domain and Negative evidence.

## Plan

## Rollback

git revert

## Journal

- 2026-10-01T19:50:27Z [implementation] — Cross-cutting hook encoding gate found two subprocess reads in untracked tests/test_cold_start_drill.py using parent locale. Added explicit UTF-8 to both while preserving drill behavior.
- 2026-10-04T10:39:38Z [implementation] — AC-1 ✓ tests/test_publication_lines.py now filters git ls-files through publication_snapshot.is_excluded and applies publication_snapshot.public_text to AGENTS.md/CLAUDE.md, so the ratchet and publisher share one boundary. AC-2 ✓ the original snapshot regressions are covered by tests/test_ci_tool_pins.py, tests/test_projection_census.py, tests/test_mypy_clean.py and tests/test_mypy_gate_scope.py; repository mypy reports success over 558 source files, and the focused development slice passed 258 with 1 named skip. AC-3 ✓ test_a_real_violation_in_a_kept_file_is_still_detected proves a kept C:\Users\ayumashev occurrence fails; test_the_scan_uses_the_production_filter_and_keeps_public_ratchets proves excluded tasks/.gitlab are absent while public ratchets remain; development-line controls executed before the temporary snapshot. AC-4 ✓ an alternate Git index included the dirty working-tree release changes, removed the 10 production exclusions, wrote filtered tree 9de3bf16b2e8b50c50b92d450901af1bbc43745d, materialized 1,731 files, initialized an index-only temporary checkout, and passed 69 focused public tests with 1 named skip; the temporary tree was then removed. AC-5 ✓ ruff and mypy are clean; audit_pytest_dedupe.py reports 0 COPY, 282 PARALLEL and 7,829/7,829 tests able to fail; CLI tausik_verify #3447 passed 8 applicable gates and 1,243 tests with 1 skip over 75/659 mapped test files. Hadolint was not applicable because no Dockerfile is in scope. Domain: public filter/test boundary plus behavior-preserving type repairs in already-dirty 1.11.1 benchmark/review modules; EN/RU changelog mirrors updated. Negative: excluded development ledger findings cannot redden the public snapshot, but the same bytes in a kept file still fail; unknown/missing benchmark values remain unknown; no publication semantics or exclusion rule changed. The scope-narrower-than-diff status names unrelated dirty release files and is bounded by the explicit relevant-files list.
