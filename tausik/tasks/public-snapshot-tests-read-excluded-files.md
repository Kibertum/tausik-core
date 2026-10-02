---
slug: public-snapshot-tests-read-excluded-files
title: "GitHub is red on 1.10.0: four tests read files the public snapshot excludes"
status: active
epic: release-110-deferred-from-19
story: release110-owner-priorities
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths:
  - "tests/"
  - "scripts/"
  - pyproject.toml
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - "changelog.d/"
  - "docs/"
  - "tausik/"
  - ".github/"
  - README.md
  - README.ru.md
scope_tools: []
depends_on: []
completed_at: null
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

GitHub Actions run 36651468953 on 43426979 (v1.10.0): all 11 jobs red on the same 4 tests — test_ci_tool_pins needs .gitlab-ci.yml, test_projection_census needs tausik/tasks, test_mypy_clean and test_mypy_gate_scope fail on cli_push_ok importing the excluded scripts/ci_lane_dev.py. The snapshot's own test run (publishing decision of session #251) was skipped at release.

## Acceptance Criteria

AC-1 Each of the 4 tests passes or skips with a named reason on the public snapshot tree. AC-2 mypy is clean on the snapshot tree. AC-3 NEGATIVE: on the development line the 4 tests still run and still fail on a real violation. AC-4 The snapshot tree is checked out and its test lane run locally BEFORE publishing 1.10.1. AC-5 GitHub Actions green on the 1.10.1 snapshot.

## Plan

## Rollback

git revert

## Journal

- 2026-10-01T19:50:27Z [implementation] — Cross-cutting hook encoding gate found two subprocess reads in untracked tests/test_cold_start_drill.py using parent locale. Added explicit UTF-8 to both while preserving drill behavior.
