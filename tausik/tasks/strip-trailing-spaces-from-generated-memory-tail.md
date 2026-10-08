---
slug: strip-trailing-spaces-from-generated-memory-tail
title: "Strip trailing spaces from generated memory tail"
status: done
epic: null
story: null
complexity: simple
role: null
stack: null
tier: null
call_budget: null
defect_of: null
scope: "Compact memory rendering for generated governance blocks."
scope_exclude: "Stored memory content and unrelated Markdown generation."
relevant_files:
  - "scripts/service_knowledge_aggregates.py"
  - "tests/test_claudemd_drift.py"
  - AGENTS.md
  - CLAUDE.md
scope_paths: []
scope_tools: []
assurance_profiles: []
assurance_impact: null
depends_on: []
completed_at: "2026-10-04T14:05:16Z"
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

Ensure dynamic governance generation never emits trailing whitespace when compact memory entries are truncated.

## Acceptance Criteria

AC-1 Generated AGENTS.md and CLAUDE.md dynamic lines have no trailing whitespace. AC-2 negative: truncation preserves the visible text boundary without leaving a trailing blank. AC-3 focused tests and git diff --check pass.

## Plan

## Rollback

Revert the injected-line trailing-whitespace trim.

## Journal

- 2026-10-04T14:04:05Z [implementation] — AC-1: flatten_for_injection strips trailing whitespace after truncation; bootstrap redeploy plus update-claudemd removed all four generated violations. AC-2: ✓ tests/test_claudemd_drift.py::test_memory_tail_truncation_never_leaves_trailing_whitespace covers a boundary space at the cut. AC-3: ✓ 15 focused tests passed and git diff --check reports no whitespace errors. Domain: regenerated governance files remain commit-clean.
- 2026-10-04T14:05:12Z [implementation] — AC-1: ✓ generated AGENTS.md and CLAUDE.md contain no trailing whitespace. AC-2: ✓ truncation boundary regression in tests/test_claudemd_drift.py passes. AC-3: ✓ verify #3510 passed 210 tests, 0 failed across 15 mapped files; git diff --check is clean; 8 gates passed, hadolint skipped as not applicable. Domain: bootstrap regeneration remains commit-clean.
