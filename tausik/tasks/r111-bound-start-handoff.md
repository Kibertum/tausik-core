---
slug: r111-bound-start-handoff
title: "1.11: bound generated handoff in the start response"
status: done
epic: release-111-economy-draft
story: release111-context-and-workflow
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 35
defect_of: session-open-envelope-90pct-noise
scope: "Session-open MCP projection, aligned behavior tests, start skill and release economy docs; local task/story metadata."
scope_exclude: "Hook dispatch repair, telemetry schema additions, root model switching, external tracker updates, commits and releases."
relevant_files:
  - "harness/claude/mcp/project/handlers_session.py"
  - "tests/test_session_open_handler.py"
  - "harness/skills/start/SKILL.md"
  - "docs/en/mcp.md"
  - "docs/ru/mcp.md"
  - "docs/ru/research/release111-economy-results.md"
  - "changelog.d/start-handoff-111.md"
scope_paths:
  - "harness/claude/mcp/project/handlers_session.py"
  - "tests/test_session_open_handler.py"
  - "harness/skills/start/SKILL.md"
  - "docs/en/mcp.md"
  - "docs/ru/mcp.md"
  - "docs/ru/research/release111-economy-results.md"
  - "changelog.d/start-handoff-111.md"
  - ".tausik/planning/release-111"
  - tausik
scope_tools: []
depends_on: []
completed_at: "2026-10-01T19:17:52Z"
resolution: null
resolution_reason: null
tracker_refs: []
started_model_id: claude-opus-5
started_model_version: null
done_model_id: claude-opus-5
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
---

## Goal

Reduce repeated startup context using the recorded session #279 response; keep actionable continuation signals and explicit access to the complete handoff.

## Acceptance Criteria

AC-1 Record before/after UTF-8 response bytes on the same frozen session #279 envelope and identify its three largest fields; reduce response by at least 60% without claiming task-cost savings. AC-2 Default handoff projection is at most 4096 UTF-8 bytes, preserves next steps/warnings preferentially, and explicitly reports omitted data with the existing full-handoff recovery call. AC-3 Full handoff retrieval and stored data remain unchanged; null/error and small handoffs retain their meaning. AC-4 Regression tests cover a long generated history, oversized Unicode warnings and recovery without silent loss; scoped verify passes. AC-5 Local release order is recorded; no tracker publication, paid benchmark or gate weakening.

## Plan

[{"step": "Freeze response and rank payload sources; record local release priorities.", "done": true}, {"step": "Add bounded handoff projection with full-data recovery and regression tests.", "done": true}, {"step": "Measure identical before/after input, run scoped verify, record evidence and close.", "done": true}]

## Rollback

Revert only this task's projection/test/docs edits; full stored handoff and full retrieval endpoint remain unchanged.

## Journal

- 2026-10-01T19:16:23Z [implementation] — Implemented bounded handoff with explicit recovery; frozen envelope 33599 to 4367 UTF-8 bytes (-87%), handoff 29954 to 1976. Largest fields: working_tree 11151, verify 5930, completed 4841. 23 scoped tests pass; dedupe audit 0 copies. Local priorities recorded; no paid benchmark or external tracker write.
- 2026-10-01T19:17:47Z [implementation] — AC-1 verified: frozen UTF-8 envelope 33599 to 4367 bytes, 87% smaller; top fields recorded in session-open-measurement-20261001.json. AC-2/3/4 verified: tests/test_session_open_handler.py::TestEnvelopeProjection::test_generated_history_is_bounded_and_fully_recoverable and test_small_and_failed_handoffs_keep_their_meaning pass. Full source/retrieval unchanged, omitted warnings force full recovery. AC-5 verified: local epic order updated; external trackers untouched. Root cause: generated handoff inventories bypassed the prior session/self-check projection; prevention: long-history and Unicode recovery regressions. Domain: context output. Negative: oversized warning is omitted explicitly and requires full read, never silently accepted. Verify #3285 passed, 39/649 mapped test files; hadolint non-applicable skipped.
- 2026-10-01T19:18:31Z [done] — AC-1: ✓ Frozen envelope reduced 33599 to 4367 UTF-8 bytes. AC-2: ✓ 4096-byte summary with explicit omissions tested. AC-3: ✓ Full handoff recovery equals original; stored object unmodified. AC-4: ✓ Long history and oversized Unicode negative regressions pass; verify #3285 green (39/649 mapped test files, hadolint skipped). AC-5: ✓ Local release priorities recorded; no external writes. Root cause (regression): generated handoff history bypassed the older envelope projection. Prevention: generated-history and oversized-warning recovery tests in tests/test_session_open_handler.py.
