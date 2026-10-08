---
slug: r111-compact-verification-output
title: "Return compact verification summaries while retaining full evidence"
status: done
epic: release-111-economy-draft
story: release111-economy-hardening
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 40
defect_of: null
scope: "Shared bounded verification renderer, durable full logs, CLI/MCP transport, behavioral fixtures, release note."
scope_exclude: null
relevant_files:
  - "scripts/render_verify.py"
  - "scripts/verify_compact_output.py"
  - "scripts/task_progress_close.py"
  - "tests/test_compact_verification_output.py"
  - "tests/test_task_progress_close.py"
  - CHANGELOG.md
scope_paths:
  - "scripts/render_verify.py"
  - "scripts/project_cli_verify.py"
  - "harness/claude/mcp/project/handlers_verification.py"
  - "tests/test_compact_verification_output.py"
  - CHANGELOG.md
  - "scripts/verify_compact_output.py"
  - ".claude/scripts/render_verify.py"
  - ".claude/scripts/verify_compact_output.py"
  - ".codex/scripts/render_verify.py"
  - ".codex/scripts/verify_compact_output.py"
  - ".qwen/scripts/render_verify.py"
  - ".qwen/scripts/verify_compact_output.py"
  - "scripts/task_progress_close.py"
  - "tests/test_task_progress_close.py"
  - ".claude/scripts/task_progress_close.py"
  - ".codex/scripts/task_progress_close.py"
  - ".qwen/scripts/task_progress_close.py"
scope_tools: []
depends_on:
  - r111-round-topology
completed_at: "2026-10-01T21:30:15Z"
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

Keep complete verification logs on disk while returning only bounded verdict, denominator, counts and actionable failures to the model context.

## Acceptance Criteria

AC-1 Successful verification output contains verdict, scope denominator, passed, skipped and deselected counts plus the evidence path. AC-2 Failure output contains a bounded number of actionable failures and a path to the complete log. AC-3 A frozen full-suite result is materially smaller than the current model-visible output while the evidence artifact remains complete. AC-4 Negative: truncation is explicit and cannot turn a failed or skipped gate into a green verdict.

## Plan

[{"step": "Freeze successful and failing verification output fixtures", "done": true}, {"step": "Implement bounded summary rendering and durable full logs", "done": true}, {"step": "Route CLI and MCP verification through the shared renderer", "done": true}, {"step": "Prove verdict integrity and measure visible-byte reduction", "done": true}]

## Rollback

git revert the compact verification renderer change

## Journal

- 2026-10-01T21:16:58Z [implementation] — Step 1 started: inspect shared CLI/MCP verification render path and durable evidence mechanisms.
- 2026-10-01T21:17:55Z [implementation] — Step 1 done: existing shared renderer is the CLI/MCP seam; gate rows retain verdict metadata but not full command output, so complete evidence will be a durable .tausik/verification artifact.
- 2026-10-01T21:17:56Z [implementation] — Step 2 started: add a bounded renderer and evidence writer behind the existing shared presentation seam.
- 2026-10-01T21:22:09Z [implementation] — Steps 2-3 done: shared render_verify now delegates CLI and MCP presentation to a bounded renderer that writes complete raw evidence; scoped behavioral tests cover success, failure, unknown counts, skip integrity, UTF-8 line bounds and payload reduction.
- 2026-10-01T21:22:10Z [implementation] — Step 4 started: run scoped verification, dedupe audit and preserve the evidence artifact path.
- 2026-10-01T21:22:42Z [implementation] — Scoped verify #3315: FAIL (expected repair). Full evidence .tausik/verification/verify-3315.log; ruff_format and bootstrap_drift failed, pytest was skipped by phase policy. Formatted the three scoped Python files; bootstrap redeploy remains outside this worker's declared ownership.
- 2026-10-01T21:23:03Z [implementation] — Redeployed normal generated profiles after root authorization; declared only renderer mirror paths before the write. Re-running scoped verify next.
- 2026-10-01T21:28:16Z [implementation] — AC-1 ✓ verify #3318 renders authoritative PASS/status, trusted mapped scope denominator, passed/skipped/deselected counts and .tausik/verification/verify-3318.log. AC-2 ✓ tests/test_compact_verification_output.py bounds 3/5 actionable failures, preserves pytest tail identity, names the full artifact, and makes evidence-write failure explicit. AC-3 ✓ frozen session-279 full-lane artifact .tausik/planning/release-111/tests-after-run.txt measured legacy 733 UTF-8 bytes → compact 607 bytes (17.2% less), with 17,583 UTF-8 raw evidence retained. AC-4 ✓ skipped gate stays visible, report['passed'] remains authoritative, unknown counts remain unknown, and truncation says so. Domain: a compact answer can guide the next repair without re-running a 12k-test lane, while the complete auditable gate output stays on disk. Tests: 78 targeted passed; ruff clean; pytest dedupe audit reports 0 copy / 282 parallel.
- 2026-10-01T21:28:28Z [implementation] — NO-DEAD-END: verify #3315 was the expected first scoped run before deterministic ruff formatting and normal profile redeploy; it preserved the actionable evidence path and was repaired by #3318.
- 2026-10-01T21:30:10Z [implementation] — AC amendment ✓ normal task_progress_close --verify now calls the same render_verify.verify_lines path: its bounded summary omits nested raw gate output while the durable artifact retains diagnostics (tests/test_task_progress_close.py). Final verify #3320: PASS, 10/654 mapped tests, 27 passed, artifact .tausik/verification/verify-3320.log. Final targeted suite: 89 passed; ruff clean; dedupe audit: 0 copy, 282 parallel.
- 2026-10-01T21:31:17Z [done] — Natural Codex observation after closure: 50 attributed response rounds; Terra Medium Standard single identity; 6699329 total tokens incl 6508032 cached input; attempts2/retries1 from project state. All observed retries retained. This task alone exceeds40 rounds; comparison with other model tasks is not causal evidence. Source: incremental usage_codex_report accepted_task_cost.
