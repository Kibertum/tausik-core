---
slug: full-lane-after-91b08e1d-two-tree-guards-caught-th
title: "Full lane after 91b08e1d: two tree guards caught the new audit scripts"
status: done
epic: null
story: null
complexity: simple
role: null
stack: null
tier: trivial
call_budget: 10
defect_of: null
scope: "Two guard-driven edits: a docstring reword and stdin=DEVNULL on two git calls; no behaviour change."
scope_exclude: "No _ALLOWED exemption; no change to what either audit measures."
relevant_files:
  - "scripts/response_contract_audit.py"
  - "scripts/context_block_audit.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-09-12T16:29:49Z"
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

test_doctor_multi_ide flagged a hardcoded IDE profile literal in response_contract_audit.py's docstring; test_risk_compute_stdin flagged two git subprocess calls in context_block_audit.py without stdin=DEVNULL. Both are tree-wide guards the scoped lane defers to the full lane by design.

## Acceptance Criteria

AC-1: tests/test_doctor_multi_ide.py::TestNoNewClaudeLiterals::test_no_unexempted_claude_literal_in_scripts green with the docstring reworded (no _ALLOWED entry). AC-2: tests/test_risk_compute_stdin.py::TestNoUnguardedSubprocessInMcpPath::test_all_top_level_subprocess_calls_set_stdin green with stdin=subprocess.DEVNULL on both calls. AC-3: full lane green except the known external renar corpus red. AC-4 (negative): the two audits still produce the same figures after the edits (7.1% / 43.6% / 37.2%) — an edit that changed a figure would be a behaviour change, and the guard-fix would be rejected.

## Plan

## Rollback

git revert of the one commit.

## Journal

- 2026-09-12T16:28:59Z [planning] — AC-1 ✓ tests/test_doctor_multi_ide.py::TestNoNewClaudeLiterals::test_no_unexempted_claude_literal_in_scripts — docstring names 'the *.jsonl files the IDE keeps per project' instead of the profile path. AC-2 ✓ tests/test_risk_compute_stdin.py::TestNoUnguardedSubprocessInMcpPath::test_all_top_level_subprocess_calls_set_stdin — stdin=subprocess.DEVNULL on git log and git show. AC-3 ✓ full lane after the two edits: 10069 passed / 21 skipped before the stdin fix with only that one red; the stdin guard file 29 passed after. Root cause (lane-scope): both guards walk the whole tree, which the scoped verify lane defers to the full lane by design — the scripts were new, so no scoped test reached them.
- 2026-09-12T16:29:46Z [implementation] — AC-4 ✓ figures unchanged after both edits: response_contract_audit 7.1% (451 answers), context_block_audit 43.6% / 37.2% (94 sessions) — re-run after the edits. Verify run #2533 signed.
