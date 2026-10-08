---
slug: make-session-update-cache-failures-nonfatal
title: "Make session update cache failures nonfatal"
status: done
epic: null
story: null
complexity: medium
role: null
stack: null
tier: null
call_budget: null
defect_of: null
scope: "Session-start update cache persistence and its regressions."
scope_exclude: "Network version comparison semantics, review routing, bootstrap governance, and benchmarks."
relevant_files:
  - "scripts/update_check.py"
  - "tests/test_update_check.py"
scope_paths: []
scope_tools: []
assurance_profiles: []
assurance_impact: null
depends_on: []
completed_at: "2026-10-04T13:39:54Z"
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

Keep authoritative session-start version decisions while preventing cache persistence errors and concurrent writers from crashing session startup.

## Acceptance Criteria

AC-1: Cache writes use unique temporary files and authoritative version decisions survive persistence errors. AC-2 negative: PermissionError or overlapping cache replacements cannot crash a session start, while a confirmed newer-version refusal remains enforced. AC-3: focused tests pass.

## Plan

## Rollback

Revert cache persistence isolation and warning handling.

## Journal

- 2026-10-04T13:39:30Z [implementation] — AC-1: cache writes use per-writer mkstemp paths and persistence errors return a warning alongside the authoritative answer. AC-2: ✓ tests/test_update_check.py::test_cache_permission_failure_warns_but_session_still_opens, ::test_cache_writers_use_unique_temporary_files, and ::test_newer_release_blocks_cli_before_a_session_row_opens cover permission, overlap, and refusal boundaries. AC-3: ✓ focused update-check tests pass. Domain: a read-only or contended cache cannot prevent normal session opening or weaken a newer-release refusal.
- 2026-10-04T13:39:50Z [implementation] — AC-1: ✓ scripts/update_check.py uses unique same-directory temporary files and returns persistence warnings. AC-2: ✓ permission, concurrent writer, and newer-release refusal regressions pass in tests/test_update_check.py. AC-3: ✓ verify #3502 passed 59 tests, 0 failed across 2 mapped files; 8 gates passed, hadolint skipped as not applicable. Domain: cache persistence is nonfatal but cannot weaken an authoritative refusal.
