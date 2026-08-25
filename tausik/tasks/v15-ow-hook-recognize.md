---
slug: v15-ow-hook-recognize
title: "Hook integration — recognize a delegated task in-session"
status: done
epic: v15-orchestrator-worker
story: v15-ow-core
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/hooks/* (session/edit hooks), integration with delegation state + scope gate, tests/test_ow_hook.py"
scope_exclude: "delegate CLI (v15-ow-delegate-cli); contract definition (v15-ow-subagent-profile)"
relevant_files:
  - "scripts/service_delegate.py"
  - "scripts/service_task.py"
  - "tests/test_ow_hook_recognize.py"
  - README.md
  - "docs/_generated/constants.json"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-14T21:16:56Z"
---

## Goal

Wire the hook layer to detect when the current session is operating on a delegated task (set by `task delegate`) and adjust behavior accordingly: activate the worker profile, enable the scope hard-gate, suppress orchestrator-only nags. Detection must be deterministic from persisted delegation state, not heuristic.

## Acceptance Criteria

AC1: task_start deterministically detects an active delegated task from persisted state (meta delegation:<slug>). AC2: on a delegated task_start it surfaces WORKER MODE — names the worker profile (trimmed WORKER_SKILLS) and that scope is hard-gated (already enforced by scope_write_gate) + points to summary-back; runtime skill-trimming is not a mid-session op, so this is a surfaced operating contract, not a re-bootstrap. AC3: orchestrator-only model-recommendation banner ('switch down to save cost') is SUPPRESSED for a delegated worker (it runs the orchestrator-chosen model by design). AC4: a non-delegated task_start is unchanged (normal banner, no worker notice). AC5: tests cover delegated→worker-notice+no-banner, non-delegated→banner+no-notice, and the pure notice helper; ruff+mypy clean; filesize<400. Negative: a delegation-lookup error degrades to normal (non-worker) task_start, never crashes start.

## Plan

## Rollback

git revert; hook branch is guarded by delegated-state check, inert for normal sessions; revert removes the branch cleanly.

## Journal

- 2026-06-14T21:15:09Z [implementation] — task_start now recognizes a delegated task (self.task_delegation, best-effort): surfaces worker_mode_notice (service_delegate) — names task+model, trimmed WORKER_SKILLS contract, scope hard-gated, report via summary-back — AND suppresses the orchestrator-only model-recommendation banner (worker runs orchestrator-chosen model by design). Non-delegated start unchanged (normal banner). Deterministic from persisted meta state; delegation-lookup error degrades to normal start. 4 tests (notice helper + delegated shows worker-mode/no-banner + non-delegated banner/no-notice). ruff+full mypy clean.
- 2026-06-14T21:15:25Z [implementation] — AC1: ✓ task_start detects active delegated task from persisted meta (self.task_delegation) — test_delegated_start_shows_worker_mode. AC2: ✓ surfaces worker mode — trimmed WORKER_SKILLS contract + scope hard-gated + summary-back pointer (worker_mode_notice) — test_notice_names_task_model_and_contract. AC3: ✓ orchestrator model-recommendation banner suppressed for delegated worker — test_delegated...suppresses_banner asserts no 'Model recommendation:'. AC4: ✓ non-delegated start unchanged (banner present, no worker notice) — test_non_delegated_start_unchanged. AC5: ✓ 4 tests; ruff+full mypy clean (210 files); files<400. Negative: delegation-lookup error → normal start (best-effort try/except). Domain: a real worker sub-agent, on task start, is told it's in worker mode with its operating contract and isn't nagged to switch model.
- 2026-06-14T21:16:55Z [implementation] — AC1: ✓ task_start detects delegated task from persisted meta via start_recognition_message — test_delegated_start_shows_worker_mode. AC2: ✓ surfaces worker mode (trimmed WORKER_SKILLS + scope hard-gated + summary-back) — worker_mode_notice, test_notice_names_task_model_and_contract. AC3: ✓ orchestrator model banner suppressed for delegated — test asserts no 'Model recommendation:'. AC4: ✓ non-delegated unchanged (banner, no notice) — test_non_delegated_start_unchanged. AC5: ✓ 4 tests (20 incl delegate/summary regression); ruff+full mypy clean (210); service_task.py 395<400 (logic extracted to service_delegate.start_recognition_message). Negative: recognition/meta error → falls back to normal banner/start, never crashes. Domain: a worker sub-agent is told its mode+contract at task start and isn't nagged to switch model.
