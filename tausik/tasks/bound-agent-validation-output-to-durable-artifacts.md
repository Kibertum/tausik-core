---
slug: bound-agent-validation-output-to-durable-artifacts
title: "Bound agent validation output to durable artifacts"
status: done
epic: null
story: null
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 60
defect_of: null
scope: "Canonical local validation runner, UTF-8 durable logs/JUnit, bounded verdict/failure projection, CLI/MCP wrappers and focused output tests."
scope_exclude: "No second verify implementation, no LLM summarizer, no hiding skipped/deselected counts, no Kiberza, GitLab10, commit, push or release."
relevant_files:
  - "scripts/gate_outcome.py"
  - "scripts/gate_command_runner.py"
  - "scripts/gate_runner.py"
  - "scripts/verify_compact_output.py"
  - "scripts/project_cli_task.py"
  - "harness/claude/mcp/project/handlers_task.py"
  - "tests/test_compact_verification_output.py"
  - "tests/test_gate_command_runner.py"
  - "tests/test_project_mcp.py"
  - "docs/en/testing-principles.md"
  - "docs/ru/testing-principles.md"
  - "docs/ru/research/bounded-validation-output-replay-111.md"
  - "changelog.d/bounded-validation-output-111.md"
scope_paths:
  - scripts
  - harness
  - "docs/en"
  - "docs/ru"
  - tests
  - changelog.d
scope_tools: []
depends_on: []
completed_at: "2026-10-02T09:52:09Z"
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

Keep complete validation evidence on disk while returning only one bounded verdict and actionable failures to the model.

## Acceptance Criteria

AC-1 Pytest, lint and verify runners persist complete UTF-8 output and machine-readable counts. AC-2 Green results return one compact verdict; red results return bounded actionable failures with artifact addresses. AC-3 Repeated polling or progress bars do not enter model context. AC-4 Natural replay shows fewer model-return boundaries without losing failure information. AC-5 Changelog and docs describe recovery of omitted detail.

## Plan

[{"step": "Map validation commands that still stream progress or require polling through model rounds", "done": true}, {"step": "Define the canonical durable artifact and bounded verdict contract", "done": true}, {"step": "Implement thin callers and preserve actionable red diagnostics", "done": true}, {"step": "Replay green and red validation flows, scoped verify, document and close", "done": true}]

## Rollback

Revert the canonical validation runner, wrapper, documentation and focused tests; durable artifacts remain removable local evidence.

## Journal

- 2026-10-01T22:58:03Z [planning] — Priority 3 after affected-test selection. Compose with the existing compact verify renderer; do not create a competing verification implementation.
- 2026-10-02T09:38:45Z [implementation] — User specification: reduce user-visible and model-visible validation text; express work as bounded TAUSIK tasks; persist complete evidence in durable UTF-8 artifacts; return compact green verdicts and bounded actionable red failures; preserve counts and quality; do not commit, push, or release.
- 2026-10-02T09:38:51Z [implementation] — Setup note: configured stack is python, but harness/stacks/python.md is absent; proceeding with repository pyproject/AGENTS conventions rather than inventing stack guidance.
- 2026-10-02T09:46:11Z [implementation] — Step 1 done: mapped model-visible validation paths. Existing verify rendering was bounded, but task-done CLI/MCP emitted per-gate progress, MCP direct close returned complete gate bodies, machine-readable counts were absent, and display head/tail could precede durable capture.
- 2026-10-02T09:46:11Z [implementation] — Step 2 done: canonical contract is one UTF-8 .log with complete gate bodies, adjacent JSON with verdict/gate/pytest counts and provenance, one compact green verdict, up to four actionable lines per shown red gate, and explicit artifact-write degradation.
- 2026-10-02T09:46:12Z [implementation] — Step 3 done: shared verify renderer writes log+JSON; command outcomes retain unfiltered artifact_detail; CLI/MCP task done suppress deterministic progress; MCP direct close strips complete bodies and points to durable evidence. Focused behavior tests: 77 passed.
- 2026-10-02T09:51:57Z [implementation] — AC verified: AC-1 ✓ tests/test_compact_verification_output.py::test_large_success_answer_is_compact_but_artifact_retains_every_byte plus verify #3350 .log/.json. AC-2 ✓ tests/test_project_mcp.py::TestTaskCRUD::test_task_done_persists_full_gate_output_but_returns_a_bounded_failure. AC-3 ✓ tests/test_project_mcp.py::TestTaskCRUD::test_task_done_does_not_stream_gate_progress_to_model_context. AC-4 ✓ real red/green replay #3348/#3350 and docs/ru/research/bounded-validation-output-replay-111.md; one final TAUSIK result, complete failure evidence retained. AC-5 ✓ EN/RU testing-principles recovery instructions and changelog.d/bounded-validation-output-111.md. Focused suite 108 passed; dedupe audit 0 literal copies; scoped verify #3350 PASS, 1591 passed, 12 skipped, 66/656 files.
- 2026-10-02T09:51:57Z [implementation] — Step 4 done: real red verify #3348 returned the 501-line filesize failure and retained full log+JSON; corrected green verify #3350 covered 66/656 test files with 1591 passed and 12 skipped. Replay is documented in docs/ru/research/bounded-validation-output-replay-111.md; host-owned transport polling is explicitly not claimed as TAUSIK savings.
- 2026-10-02T09:52:21Z [done] — Domain: real verify artifacts #3348 and #3350 were physically read as UTF-8 and their JSON sidecars parsed; red evidence named the actual 501-line defect and green counts matched the visible verdict. The behavior is not fixture-only.
