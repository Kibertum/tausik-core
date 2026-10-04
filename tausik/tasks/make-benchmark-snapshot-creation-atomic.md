---
slug: make-benchmark-snapshot-creation-atomic
title: "Make benchmark snapshot creation atomic"
status: done
epic: null
story: null
complexity: simple
role: null
stack: null
tier: null
call_budget: null
defect_of: release-tausik-1-11-1
scope: "scripts/benchmark_compare_support.py, MCP benchmark handler boundary, and aligned comparison tests"
scope_exclude: "No change to snapshot contents, allowed directory, or comparison semantics"
relevant_files:
  - "scripts/benchmark_compare_support.py"
  - "harness/claude/mcp/project/handlers_status.py"
  - "tests/test_benchmark_compare.py"
scope_paths: []
scope_tools: []
assurance_profiles: []
assurance_impact: null
depends_on: []
completed_at: "2026-10-04T13:02:21Z"
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

Guarantee MCP comparison snapshots cannot overwrite an existing artifact under concurrent creation.

## Acceptance Criteria

AC-1 snapshot persistence uses atomic exclusive creation. AC-2 competing creation attempts yield one success and one refusal. AC-3 fixed project-owned path and traversal protections remain intact. Negative: an existing snapshot is never truncated or replaced, including under a race.

## Plan

## Rollback

Revert exclusive snapshot persistence and tests.

## Journal

- 2026-10-04T13:01:41Z [implementation] — Focused verification: ruff passed and 15 comparison/MCP tests passed; a barrier-synchronized two-writer regression produces exactly one artifact and one FileExists refusal.
- 2026-10-04T13:01:41Z [implementation] — Root cause (race-condition): the MCP boundary checked target.exists() separately from write_text(), so two processes could both pass the check and the later truncating write could replace the first snapshot. Prevention: persist snapshots with pathlib exclusive x-mode and keep the path-boundary precheck only for early diagnostics.
- 2026-10-04T13:02:17Z [implementation] — ✓ AC-1 benchmark_compare_support.persist_snapshot uses pathlib x-mode exclusive creation. ✓ AC-2 tests/test_benchmark_compare.py::test_snapshot_creation_is_atomic_under_competing_writers proves one success and one refusal. ✓ AC-3 MCP traversal, absolute-path, first-write, and overwrite-refusal tests remain green. ✓ Negative: an existing snapshot is never opened in truncating mode. Domain: exclusive create delegates race arbitration to the filesystem. Verify: verification_run #3492 passed 279 tests with 8 gates passed.
