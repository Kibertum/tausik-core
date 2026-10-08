---
slug: constrain-mcp-benchmark-snapshot-writes-to
title: "Constrain MCP benchmark snapshot writes to project artifacts"
status: done
epic: null
story: null
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: compare-project-version-model-economics
scope: "harness/claude/mcp/project/handlers_status.py, MCP tool schema for metrics comparison, benchmark snapshot path helper if needed, and aligned tests."
scope_exclude: "No benchmark formulas, cohort selection, unrelated MCP handlers, or public release actions."
relevant_files:
  - "harness/claude/mcp/project/handlers_status.py"
  - "tests/test_benchmark_compare.py"
scope_paths: []
scope_tools: []
assurance_profiles: []
assurance_impact: null
depends_on: []
completed_at: "2026-10-04T12:01:45Z"
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

Prevent benchmark comparison MCP calls from writing outside a fixed project-owned artifact directory or overwriting arbitrary paths.

## Acceptance Criteria

AC-1 Absolute paths and traversal are rejected at the MCP boundary. AC-2 Valid project-owned snapshot destinations still work. AC-3 Tests exercise absolute, traversal, overwrite, and valid cases. Negative: no caller-controlled path can escape the allowed artifact root.

## Plan

## Rollback

Revert the focused fix commit; retain the release block until a replacement fix passes review and verification.

## Journal

- 2026-10-04T11:57:53Z [implementation] — Implemented fixed project-owned artifact directory, basename-only resolution, overwrite refusal, explicit MCP schema, and absolute/traversal/valid/overwrite behavior tests. Focused result: 13 passed.
- 2026-10-04T12:01:13Z [implementation] — AC verified: AC-1 ✓ handlers_status resolves only one basename beneath .tausik/artifacts/benchmark-comparisons and rejects absolute/traversal paths. AC-2 ✓ valid snapshot created and JSON verified. AC-3 ✓ parametrized traversal plus absolute, overwrite, and valid behavior tests; focused 13 passed, scoped verify #3467 passed 277 tests. Negative ✓ target parent equality and no-overwrite checks prevent escape and replacement.
- 2026-10-04T12:01:28Z [implementation] — Root cause (missing-validation): MCP comparison passed caller-controlled snapshot_path directly to a filesystem writer. Prevention: resolve a basename under a fixed project-owned directory, reject absolute/traversal paths and refuse overwrite at the boundary.
- 2026-10-04T12:01:38Z [implementation] — NO-DEAD-END: remaining red verifies were expected stale deployed profiles/static formatting before bootstrap and ruff preparation; the final prepared scoped verify #3467 is green.
