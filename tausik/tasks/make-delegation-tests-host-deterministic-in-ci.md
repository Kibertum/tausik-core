---
slug: make-delegation-tests-host-deterministic-in-ci
title: "Make delegation tests host-deterministic in CI"
status: done
epic: null
story: null
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "tests/conftest.py and delegation behavior test modules"
scope_exclude: "production scripts"
relevant_files:
  - "tests/test_ow_delegate.py"
  - "tests/test_ow_e2e.py"
  - "tests/test_ow_handoff.py"
  - "tests/test_ow_hook_recognize.py"
  - "tests/test_v15_test_gaps.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths:
  - "tests/test_ow_delegate.py"
  - "tests/test_ow_e2e.py"
  - "tests/test_ow_handoff.py"
  - "tests/test_ow_hook_recognize.py"
  - "tests/test_v15_test_gaps.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-10-02T16:42:54Z"
resolution: null
resolution_reason: null
tracker_refs: []
started_model_id: gpt-6-astra
started_model_version: null
done_model_id: gpt-6-astra
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
---

## Goal

Keep delegation behavior tests independent of the machine host while preserving the advisory guard for unsupported hosts.

## Acceptance Criteria

1. Delegation behavior fixtures explicitly use a spawn-capable Codex host. 2. The unsupported-host test still proves fail-closed advisory behavior. 3. The focused affected tests pass on a clean environment. Negative: production host detection is not weakened and no duplicate tests are added.

## Plan

## Rollback

git revert the test-fixture commit

## Journal

- 2026-10-02T16:30:59Z [implementation] — Root cause: delegation behavior tests inherited local host detection; clean GitHub checkout correctly resolved unknown and hit the 1.11 advisory guard. Added one explicit spawn_capable_host fixture and applied it only to delegation behavior modules; no production code or test count changed. Focused result: 39 passed. Dedupe audit: 0 copies.
- 2026-10-02T16:42:32Z [implementation] — AC evidence: tests/test_ow_delegate.py, tests/test_ow_e2e.py, tests/test_ow_handoff.py, tests/test_ow_hook_recognize.py and tests/test_v15_test_gaps.py each set Codex only in their autouse behavior fixture. tests/test_ow_delegate.py::TestTaskDelegate::test_unverified_host_is_advisory_and_never_delegated still injects an advisory Kilo route and proves no delegation is recorded. Verify #3403 passed all 39 selected nodes; 0 new nodes; production scripts unchanged.
- 2026-10-02T16:42:40Z [implementation] — AC verified: 1. PASS — five delegation behavior modules explicitly pin Codex in local autouse fixtures. 2. PASS — test_unverified_host_is_advisory_and_never_delegated still injects advisory Kilo and asserts no record. 3. PASS — verify #3403 selected 39 nodes and all 39 passed. Negative: production scripts unchanged and test count unchanged.
