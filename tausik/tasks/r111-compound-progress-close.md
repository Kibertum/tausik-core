---
slug: r111-compound-progress-close
title: "Compound deterministic progress and closure operations"
status: done
epic: release-111-economy-draft
story: release111-economy-hardening
complexity: complex
role: developer
stack: python
tier: substantial
call_budget: 90
defect_of: null
scope: "Compose existing task_log, task_step, verify and task_done operations into one deterministic progress/close service path with thin CLI/MCP wrappers and workflow guidance."
scope_exclude: "No database schema, gate semantics, verification cache/handle implementation, hooks, unrelated host profiles, external trackers, release metadata or generated site changes."
relevant_files:
  - "scripts/task_progress_close.py"
  - "scripts/project_cli_task.py"
  - "scripts/project_parser_task.py"
  - "harness/claude/mcp/project/handlers_task.py"
  - "harness/claude/mcp/project/tools.py"
  - "harness/skills/task/SKILL.md"
  - "harness/skills/ship/SKILL.md"
  - "tests/test_task_progress_close.py"
  - "docs/ru/cli-tasks.md"
  - "changelog.d/compound-progress-close-111.md"
scope_paths:
  - "scripts/task_progress_close.py"
  - "scripts/project_cli_task.py"
  - "scripts/project_parser_task.py"
  - "harness/claude/mcp/project/handlers_task.py"
  - "harness/claude/mcp/project/tools.py"
  - "harness/skills/task/SKILL.md"
  - "harness/skills/ship/SKILL.md"
  - "tests/test_task_progress_close.py"
  - "docs/ru/cli-tasks.md"
  - "changelog.d/compound-progress-close-111.md"
scope_tools: []
depends_on:
  - r111-round-topology
completed_at: "2026-10-01T21:15:48Z"
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

Collapse deterministic progress logging, plan advancement, verification evidence and closure transitions so normal work does not return to the model between operations that require no judgment.

## Acceptance Criteria

AC-1 The compound path delegates to existing service methods and does not create a second task-state implementation. AC-2 A frozen successful replay removes at least two model response boundaries relative to the current sequence. AC-3 Failure preserves the same task state and diagnostic evidence as the equivalent individual operations. AC-4 Negative: a red verify, incomplete plan, missing AC evidence or stale handle cannot close the task.

## Plan

[{"step": "Specify allowed deterministic operation ordering and failure semantics", "done": true}, {"step": "Implement the service composition and thin transports", "done": true}, {"step": "Update workflow skills to choose the compound path", "done": true}, {"step": "Replay green and red closure paths and measure removed boundaries", "done": true}]

## Rollback

Revert the compound composer, wrappers, guidance, tests and changelog; individual task log/step/verify/done operations remain the fallback.

## Journal

- 2026-10-01T20:58:00Z [implementation] — Step 1 done: allowed order is task_log -> task_step -> optional run_verify_for_task -> task_done. Invalid compound shape is refused before writes; once execution starts there is no rollback. Any failure envelope names the stage and preserves earlier log/step writes plus verification records exactly as the equivalent individual sequence. Green replay target is four model returns collapsed to one (three boundaries).
- 2026-10-01T21:12:09Z [implementation] — Step 2 done: canonical service composition, thin CLI/MCP wrappers, real transport parity and refusal behavior are implemented; 18 targeted and surface-ratchet tests pass.
- 2026-10-01T21:12:13Z [implementation] — Step 3 done: task and ship skills select compound progress/close where deterministic, and RU CLI docs document ordering, partial durability, failure exits, and stale-handle refusal.
- 2026-10-01T21:15:22Z [implementation] — AC-1: ✓ scripts/task_progress_close.py delegates task_log, task_step, run_verify_for_task and task_done; CLI/MCP wrappers share it. AC-2: ✓ frozen green replay compares four real legacy returns with one compound return, identical state/logs/verification, removing three model-return boundaries. AC-3: ✓ red twin-database replay proves identical partial state and verification diagnostics. AC-4: ✓ parametrized tests refuse red verify, incomplete plan, missing evidence and stale handle; invalid types/unknown keys mutate nothing; failed CLI exits 1. Tests: 18 targeted and MCP surface-ratchet checks passed; dedupe audit reports 0 copy; scoped verify #3312 passed ruff, format, class surface, bootstrap drift, docs and pytest over 55/653 mapped test files. Domain: deterministic task progress and closure transitions. Scope note: AGENTS.md was changed by the root checkpoint outside this assignment and is the one non-blocking undeclared file recorded by receipt #3312.
- 2026-10-01T21:15:22Z [implementation] — Step 4 done: frozen green and red twin-database replays prove equivalent durable state and three removed response boundaries; scoped verification is green.
- 2026-10-01T21:15:44Z [implementation] — AC-1: ✓ tests/test_task_progress_close.py::test_cli_and_mcp_progress_wrappers_have_identical_durable_state proves both wrappers use the same durable operations. AC-2: ✓ tests/test_task_progress_close.py::test_green_replay_matches_four_real_operations_and_removes_three_boundaries proves four real legacy returns become one with equivalent state. AC-3: ✓ tests/test_task_progress_close.py::test_red_verify_preserves_same_partial_state_and_diagnostic_as_separate_calls proves failure parity. AC-4: ✓ tests/test_task_progress_close.py::test_close_refusals_keep_task_open_with_no_success_flag covers red/incomplete/missing/stale refusals. Tests: 18 passed in targeted plus MCP surface ratchet; scoped verify #3312 passed ruff, format, class surface, bootstrap drift, docs and pytest over 55/653 mapped test files. Domain: deterministic task progress and closure transitions. Scope note: receipt #3312 records only root-owned AGENTS.md outside this task scope, non-blocking per Decision #138.
- 2026-10-01T21:17:00Z [done] — Natural Codex observation after closure: 99 attributed response rounds; Sol Medium Standard single identity; 12962828 total tokens incl 12736640 cached input. One task-start attempt; failed then successful closure stayed inside the window. This task exceeds the 40-round target; no causal savings claim. Source: incremental usage_codex_report accepted_task_cost.
