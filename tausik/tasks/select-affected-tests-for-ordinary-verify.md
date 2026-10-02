---
slug: select-affected-tests-for-ordinary-verify
title: "Select affected tests for ordinary verify"
status: done
epic: null
story: null
complexity: complex
role: null
stack: null
tier: moderate
call_budget: 32
defect_of: null
scope: "Existing verify test mapping, source/fixture/dependency impact evidence, fail-open selection, security-sensitive exceptions, reports and focused selector tests."
scope_exclude: "No paid model benchmark, no silent under-selection, no removal of full release lanes, no Kiberza, GitLab10, commit, push or release."
relevant_files:
  - "scripts/affected_test_selection.py"
  - "scripts/gate_command_runner.py"
  - "scripts/gate_outcome.py"
  - "scripts/service_host_context.py"
  - "tests/test_affected_test_selection.py"
  - "tests/test_gate_command_runner.py"
  - "tests/test_gates.py"
  - "tests/test_host_context_budget.py"
  - "docs/en/testing-principles.md"
  - "docs/ru/testing-principles.md"
  - "changelog.d/affected-tests-ordinary-verify-111.md"
scope_paths:
  - scripts
  - tests
  - "docs/en"
  - "docs/ru"
  - changelog.d
  - pyproject.toml
scope_tools: []
depends_on: []
completed_at: "2026-10-02T09:25:57Z"
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

Make ordinary task verification execute the smallest defensible affected-test set while retaining a fail-open path and reserving complete lanes for release cadence.

## Acceptance Criteria

AC-1 Selection explains every chosen test from changed source, fixture or declared dependency evidence. AC-2 Unknown config, dependency and selector state fails open to the complete applicable lane. AC-3 Security-sensitive changes retain the stricter existing coverage. AC-4 A real-task replay demonstrates fewer executed tests and equal verdict. AC-5 Changelog and operator guidance name when complete lanes still run.

## Plan

[{"step": "Measure current scoped verify over-selection on three real completed tasks", "done": true}, {"step": "Choose the smallest fail-open impact evidence compatible with fixtures and subprocess tests", "done": true}, {"step": "Implement selection and an explanation artifact without expanding model output", "done": true}, {"step": "Replay verdict equivalence, scoped verify, document and close", "done": true}]

## Rollback

Disable affected-test selection and restore the current scoped/full pytest command path.

## Journal

- 2026-10-01T22:58:03Z [planning] — Priority 2 after the context guard. Use current scoped-verify evidence and fail open; do not introduce a new full-suite run into ordinary task closure.
- 2026-10-02T09:15:13Z [implementation] — Measured current over-selection on three real completed tasks.
- 2026-10-02T09:15:13Z [implementation] — Step 1 done: measured current file-scoped selector on three real completed 1.11 tasks. guard-host-context-budget-before-session-reopen selects 47/655 test files and verify #3341 executed 1026 passed, 12 skipped, 23 deselected; r111-compact-verification-output selects 10/655; r111-compound-progress-close selects 55/655.
- 2026-10-02T09:15:13Z [implementation] — Step 2 done: selected deterministic file-level impact evidence (changed test, basename, direct import, CROSSCUTTING_SCOPE, observed coverage) plus pytest fixture reach from changed conftest.py. Invalid test-root config, malformed candidate/declaration, unmapped Python source and security-sensitive scope fail open to the complete applicable pytest lane; absence of a test root remains an explicit could-not-run.
- 2026-10-02T09:15:14Z [implementation] — Defined fail-open evidence boundary for source, fixture, declarations and security.
- 2026-10-02T09:21:06Z [implementation] — Implemented affected selection, fail-open execution and bounded durable explanation.
- 2026-10-02T09:21:06Z [implementation] — Step 3 done: added affected_test_selection as the single planning layer over the existing resolver; ordinary pytest now emits a content-addressed .tausik/evidence/affected-tests-<digest>.json with per-test reasons and returns only its path. Basename evidence is limited to Python source (docs/en/mcp.md no longer selects every test_mcp_*.py); changed conftest.py selects its pytest fixture subtree. Unknown config/dependency/source and security-sensitive scopes execute the complete applicable default lane.
- 2026-10-02T09:25:45Z [implementation] — AC verified: AC-1 tests/test_affected_test_selection.py::test_every_affected_test_carries_its_selection_evidence and content-addressed .tausik/evidence artifact. AC-2 parametrized uncertainty matrix plus full-lane command test. AC-3 security case widens to complete applicable lane and upstream cache/handle restrictions remain. AC-4 real replay #3341 versus new 706/12 PASS. AC-5 EN/RU testing-principles and changelog.d/affected-tests-ordinary-verify-111.md. Negative: non-Python basename collision is excluded; malformed inputs widen, not narrow. Domain: ordinary task verification executes fewer real tests while retaining the same verdict.
- 2026-10-02T09:25:45Z [implementation] — Step 4 replay: guard-host-context-before-session-reopen old verify #3341 selected 47 files and reported 1026 passed, 12 skipped; new selector selected 29 files and reported 706 passed, 12 skipped, same PASS. Reduction: 18 test files and 308 executed/skipped cases (29.7%) without a verdict change. Formal verify #3346 PASS: 31/656 files, 875 passed, 12 skipped; ruff, format, mypy, dedupe and pytest green; evidence .tausik/verification/verify-3346.log.
