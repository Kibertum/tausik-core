---
slug: r111-verify-batch-counts
title: "Count independent pytest batches in compact verification output"
status: done
epic: release-111-economy-draft
story: release111-economy-hardening
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: r111-compact-verification-output
scope: null
scope_exclude: null
relevant_files:
  - "scripts/verify_compact_output.py"
  - "tests/test_compact_verification_output.py"
  - CHANGELOG.md
scope_paths:
  - "scripts/verify_compact_output.py"
  - "tests/test_compact_verification_output.py"
  - CHANGELOG.md
  - ".claude/scripts/verify_compact_output.py"
  - ".codex/scripts/verify_compact_output.py"
  - ".qwen/scripts/verify_compact_output.py"
scope_tools: []
depends_on: []
completed_at: "2026-10-01T22:10:04Z"
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

Report aggregate pytest counts across independent batch sessions while keeping progress echoes uncounted, unknown values explicit, and full raw evidence durable.

## Acceptance Criteria

AC-1 The frozen verify-3330 raw output reports aggregate passed/skipped/deselected counts across independent pytest batches. AC-2 Echo/progress lines do not double-count a completed batch and separate deselected lines remain attached to the correct session. AC-3 Unknown count kinds render as unknown, never zero; CLI, MCP and compound routes share the result. AC-4 A parametrized behavioral matrix and scoped verify prove the fix. Negative: repeated progress/echo lines and absent count kinds cannot inflate totals or become zero.

## Plan

## Rollback

git revert the batch-count aggregation change

## Journal

- 2026-10-01T22:06:51Z [planning] — Started from observed verify-3330 regression: renderer retained only the final batch count (58) although raw evidence contains multiple independent pytest summaries.
- 2026-10-01T22:09:39Z [implementation] — AC-1 ✓ frozen live verify-3330 raw summaries aggregate to passed=2116, skipped=12, deselected=unknown rather than the previous final-batch 58/12; direct regression test uses its 25 actual terminal totals. AC-2 ✓ parametrized matrix covers single, multibatch, repeated echo, and multiline deselected outcomes; session boundary is xdist start after a terminal result. AC-3 ✓ counts only pytest output, preserves unknown kinds, and remains shared by CLI/MCP/compound through render_verify. AC-4 ✓ 89 targeted tests passed, ruff clean; scoped verify #3331 PASS with .tausik/verification/verify-3331.log; dedupe audit 0 copy/282 parallel. Domain: a 100-file mapped verify must report every batch it ran, so the compact answer remains a complete decision signal without raw-output replay.
- 2026-10-01T22:10:03Z [implementation] — Root cause (logic-error): _test_counts kept the latest count for the whole concatenated pytest gate, conflating independent runner batches with repeated output inside one batch. Prevention: segment on an xdist start after a terminal summary, then retain the latest count per kind only within that session.
