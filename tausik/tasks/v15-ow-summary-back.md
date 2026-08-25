---
slug: v15-ow-summary-back
title: "Summary-back — worker result returns to orchestrator via task_log"
status: done
epic: v15-orchestrator-worker
story: v15-ow-core
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "summary serialization on worker done, task_log/handoff integration, tests/test_ow_summary.py"
scope_exclude: "scope gate (v15-ow-scope-hardgate); docs (v15-ow-docs-tests)"
relevant_files:
  - "scripts/service_delegate.py"
  - "scripts/project_cli_task.py"
  - "scripts/project_parser_task.py"
  - "tests/test_ow_summary_back.py"
  - README.md
  - "docs/_generated/constants.json"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-14T20:52:31Z"
---

## Goal

On worker completion, persist a structured summary back to the delegated task (via task_log / handoff) so the orchestrator picks it up without re-reading the worker's full transcript: what changed, gate status, AC evidence, follow-ups. Closes the orchestrator-worker loop.

## Acceptance Criteria

AC1: on worker completion a structured summary (changed files, gate status, AC evidence, follow-ups) is persisted to the delegated task via task_log/handoff. AC2: orchestrator can read the summary without the worker transcript. AC3: missing fields degrade gracefully, never crash. AC4: tests in tests/test_ow_summary.py; filesize<400; stdlib-only.

## Plan

## Rollback

git revert; summary write is additive append to task notes/handoff, no destructive change.

## Journal

- 2026-06-14T20:51:52Z [implementation] — Implemented worker→orchestrator summary-back. service_delegate.task_summary_back(slug, summary, *, changed/gates/ac_evidence/follow_ups) → stores structured record in meta (worker_summary:<slug>) for transcript-free retrieval + appends [worker-summary] line to task_log (phase=review). task_worker_summary reads (json, None on bad). CLI `task summary-back <slug> <summary> [--changed --gates --ac-evidence --follow-ups]`; task show surfaces worker-summary line. 6 tests; CLI wired post-bootstrap. ruff/mypy clean, files<400. Closes the core OW loop: delegate → handoff → summary-back.
- 2026-06-14T20:52:12Z [implementation] — AC1: ok worker completion persists structured summary (summary/changed/gates/ac_evidence/follow_ups/at) to meta + task_log via task_summary_back — test_records_structured_summary, test_summary_appended_to_task_log. AC2: ok orchestrator reads it transcript-free via task show / task_worker_summary — surfaced in show; test_records_structured_summary. AC3: ok missing fields degrade to empty, never crash — test_optional_fields_default_empty, test_corrupt_summary_meta_returns_none. AC4: ok 6 tests; service_delegate 154 lt400; stdlib-only; CLI wired post-bootstrap. Domain: closes the OW loop delegate to handoff to summary-back; orchestrator sees worker result without reading the sub-agent transcript. Negative: unknown task ServiceError; corrupt meta to None; no summary to None.
- 2026-06-14T20:52:23Z [implementation] — AC verified: 1. ✓ task_summary_back persists structured summary (summary/changed/gates/ac_evidence/follow_ups/at) to meta worker_summary:<slug> + task_log [worker-summary] line — test_records_structured_summary + test_summary_appended_to_task_log. 2. ✓ orchestrator reads transcript-free via task_worker_summary / task show surface — test_records_structured_summary. 3. ✓ missing fields → empty, corrupt meta → None, never crash — test_optional_fields_default_empty + test_corrupt_summary_meta_returns_none. 4. ✓ 6 tests, service_delegate 154<400, CLI wired post-bootstrap. Negative: unknown task → ServiceError (test_unknown_task_raises). Domain: closes OW loop delegate→handoff→summary-back.
