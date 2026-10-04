---
slug: bind-review-records-to-the-reviewed-task-and-file
title: "Bind review records to the reviewed task and file state"
status: done
epic: null
story: null
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: route-ship-by-residual-assurance
scope: "Review record schema/migrations, review recording and closure validation, state fingerprint helpers, CLI/MCP surfaces if required, and aligned tests."
scope_exclude: "No change to review severity rules, model-family policy, unrelated verification receipts, or release publication."
relevant_files:
  - "scripts/backend_schema.py"
  - "scripts/backend_migrations_v72.py"
  - "scripts/backend_migrations.py"
  - "scripts/review_routing.py"
  - "scripts/backend_crud.py"
  - "scripts/service_review_gate.py"
  - "tests/test_review_routing.py"
scope_paths: []
scope_tools: []
assurance_profiles: []
assurance_impact: null
depends_on: []
completed_at: "2026-10-04T12:08:32Z"
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

Make closure reject a review record after substantive task, assurance, or reviewed-file state changes.

## Acceptance Criteria

AC-1 Review records persist a stable reviewed-state fingerprint. AC-2 closure accepts only a record matching current task and file state. AC-3 a regression test changes reviewed state after review and closure refuses it. Negative: an old clean review cannot authorize changed code.

## Plan

## Rollback

Revert the focused fix commit; retain the release block until a replacement fix passes review and verification.

## Journal

- 2026-10-04T12:08:18Z [implementation] — Root cause (integration-mismatch): review persistence recorded route metadata but no identity of the task contract or files actually reviewed, so closure could reuse stale evidence. Prevention: persist a deterministic reviewed-state fingerprint and recompute it at closure.
- 2026-10-04T12:08:28Z [implementation] — AC verified: AC-1 ✓ migration v72 stores reviewed_state_fingerprint computed from 15 substantive task fields and relevant-file bytes. AC-2 ✓ service_review_gate recomputes against the service project and refuses missing/mismatched fingerprints. AC-3 ✓ parametrized test mutates a reviewed file and task title; both return stale. Negative ✓ legacy unbound records and changed state cannot authorize closure. Scoped critical verify #3470: 2,454 passed, 2 skipped, 1 deselected over 126/659 test files.
- 2026-10-04T12:08:28Z [implementation] — NO-DEAD-END: the only intermediate red was the deterministic 500-line filesize cap after registering migration v72; removing surplus blank lines preserved the design.
