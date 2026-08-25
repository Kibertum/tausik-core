---
slug: v15-ow-docs-tests
title: "Orchestrator-worker — end-to-end docs + integration tests"
status: done
epic: v15-orchestrator-worker
story: v15-ow-core
complexity: medium
role: tech-writer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "docs/{en,ru}/*, tests/test_ow_e2e.py, doc-count sync"
scope_exclude: "implementation logic (lands in the 5 prior tasks)"
relevant_files:
  - "tests/test_ow_e2e.py"
  - "docs/en/architecture.md"
  - "docs/ru/architecture.md"
  - README.md
  - "docs/_generated/constants.json"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-14T21:20:26Z"
---

## Goal

Document the orchestrator-worker workflow (when/how the coordinator delegates, the handoff contract, the scope hard-gate) in docs/{en,ru} and add an end-to-end integration test covering delegate -> recognize -> scope-gate -> summary-back. Ties the 5 implementation tasks into a verified, documented whole.

## Acceptance Criteria

AC1: docs/{en,ru} document the orchestrator-worker workflow (delegate → handoff contract → in-session recognition → scope hard-gate → summary-back) + the complexity<=medium delegable rule. AC2: an end-to-end integration test drives delegate → task_start recognition → scope-gate decision → summary-back on one task and asserts each step. AC3: gen_doc_constants --check green; doc-count consumers synced. AC4: filesize<400; full bootstrap run. AC5: covered by the e2e test. Negative: the e2e asserts a COMPLEX task is REFUSED delegation and a delegated task with no scope is flagged by the scope gate — the unhappy paths, not just the golden path.

## Plan

## Rollback

git revert; docs+tests only, no runtime behavior to undo.

## Journal

- 2026-06-14T21:20:09Z [implementation] — e2e test tests/test_ow_e2e.py: full loop on one task (delegate→handoff contract→task_start worker-mode recognition+banner-suppressed→scope-gate in/out decision→summary-back) + unhappy paths (complex refused, delegated-no-scope flagged). Docs: orchestrator-worker section in architecture.md EN+RU (workflow table: delegate/handoff/recognition/scope-hardgate/summary-back + complexity<=medium rule + meta-backed CLI-first state). 3 e2e tests; gen_doc_constants green (4313); full ruff/mypy clean; bootstrap run. Completes the orchestrator-worker epic (6/6).
- 2026-06-14T21:20:26Z [implementation] — AC1: ✓ docs/{en,ru}/architecture.md document the OW workflow (delegate→handoff→recognition→scope-hardgate→summary-back table + complexity<=medium rule + meta-backed CLI-first state). AC2: ✓ e2e test_ow_e2e.py::TestHappyPath::test_full_loop drives delegate→task_start recognition→scope-gate decision→summary-back, asserting each step. AC3: ✓ gen_doc_constants --check green (4313). AC4: ✓ filesize<400 all; full bootstrap run. AC5: ✓ 3 e2e tests. Negative: TestUnhappyPaths — complex task refused delegation (test_complex_refused_delegation) + delegated-without-scope flagged by the gate (test_delegated_without_scope_is_flagged). Domain: the documented + tested flow matches the shipped CLI (delegate/handoff/summary-back) and hook (scope_write_gate) behavior. Completes orchestrator-worker epic 6/6.
