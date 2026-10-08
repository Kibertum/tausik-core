---
slug: r111-release-quality-lanes
title: "Run 1.11 release quality lanes"
status: done
epic: release-111-economy-draft
story: release111-release-proof
complexity: medium
role: qa
stack: null
tier: null
call_budget: null
defect_of: null
scope: "QA evidence and assigned integration remediation: preserve initial and rerun UTF-8 lane logs/JUnit artifacts and final report; mypy/signature repairs in scripts/work_packet.py, scripts/service_delegate.py, harness/claude/mcp/project/handlers_task.py, scripts/project_cli_task.py; compact verifier and consumer output compatibility; cold-start task-linked decision handoff; canonical stale-memory correction by root."
scope_exclude: "No pytest before QUIESCENT; no runtime/config/bootstrap edits; no release close, commit, push, paid benchmark, synthetic route start, or model causal claim."
relevant_files:
  - "scripts/work_packet.py"
  - "scripts/service_delegate.py"
  - "harness/claude/mcp/project/handlers_task.py"
  - "scripts/project_cli_task.py"
  - "scripts/task_progress_close.py"
  - "scripts/verify_compact_output.py"
  - "scripts/handoff_generate.py"
  - "tests/test_cold_start_drill.py"
  - "tests/test_consumer_first_close.py"
  - "tests/test_task_progress_close.py"
  - "tests/test_work_packet.py"
  - "tests/test_ow_delegate.py"
  - "tests/test_mypy_clean.py"
  - "tests/test_mypy_gate_scope.py"
  - "tests/test_verify_summary_honesty.py"
  - "tests/test_repo_hygiene_ratchet.py"
  - "tausik/memory/first-live-compound-closure-used-test-counts-and-file-names.md"
scope_paths:
  - ".tausik/verification/*"
  - "docs/ru/research/*"
  - "changelog.d/*"
  - "scripts/handoff_generate.py"
  - "tests/test_cold_start_drill.py"
  - "scripts/work_packet.py"
  - "scripts/service_delegate.py"
  - "harness/claude/mcp/project/handlers_task.py"
  - "scripts/project_cli_task.py"
  - "scripts/verify_compact_output.py"
  - "tests/test_consumer_first_close.py"
  - "tests/test_mypy_clean.py"
  - "tests/test_mypy_gate_scope.py"
  - "tests/test_verify_summary_honesty.py"
  - "tests/test_repo_hygiene_ratchet.py"
  - ".tausik/memory/*"
  - "tausik/memory/first-live-compound-closure-used-test-counts-and-file-names.md"
  - "scripts/task_progress_close.py"
  - "tests/test_task_progress_close.py"
  - "tests/test_work_packet.py"
  - "tests/test_ow_delegate.py"
scope_tools: []
depends_on: []
completed_at: "2026-10-01T22:55:56Z"
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

Run the user-required default and slow pytest lanes sequentially after quiescence, retain complete UTF-8 stdout and stderr logs plus JUnit artifacts, and publish an evidence-backed report without treating either cohort as a causal model comparison.

## Acceptance Criteria

AC-1 Initial default lane evidence is preserved as UTF-8 stdout+stderr and JUnit artifacts with exit status, passed, skipped, and deselected counts. AC-2 Initial slow lane evidence is preserved separately with the same fields. AC-3 After assigned fixes and one scoped QA verify, rerun default then slow lanes sequentially via a Python subprocess with PYTHONIOENCODING=utf-8 and PYTHONUTF8=1 writing binary UTF-8 stdout+stderr logs and separate JUnit XML; report each exit status and passed, skipped, deselected counts. AC-4 The final report names commands, artifact paths, timestamps, route recommendation/native identity, first-run and rerun failures or skips, and worker work outside the native root window; it makes no causal cost claim. AC-5 Cold-start handoff retains task-linked decisions across a session boundary; tests/test_cold_start_drill.py demonstrates the regression and fix without broadening decision visibility beyond that task. AC-6 Mypy is clean in scripts/work_packet.py, scripts/service_delegate.py, harness/claude/mcp/project/handlers_task.py, and scripts/project_cli_task.py; canonical signatures preserve existing behavior. AC-7 Compact verification output has one canonical gate-verdict source and tests/test_consumer_first_close.py accepts the resulting compact output. AC-8 Root corrects the stale memory reference through the canonical memory service. Negative: no fixture routing rows count as natural starts, no split default/slow task cohort, no initial artifact overwrite, and no model causal claim.

## Plan

[{"step": "Record current route recommendation and native identity", "done": true}, {"step": "After QUIESCENT, run default pytest lane with durable UTF-8 log and JUnit XML", "done": true}, {"step": "Run slow pytest lane after default with separate durable UTF-8 log and JUnit XML", "done": true}, {"step": "Publish report, log AC evidence, scoped verify, and close only if both lanes meet AC", "done": true}]

## Rollback

remove only newly created QA evidence artifacts and report if superseded

## Journal

- 2026-10-01T22:19:46Z [implementation] — Natural QA start recorded at 2026-10-01T22:19:15Z: recommended GPT-5.6 Terra Medium Standard, host=codex, route_reason=bounded simple/medium worker work defaults to Terra, no escalation. Native identity resolved as gpt-5.6-terra via provider:codex; fixture rows excluded.
- 2026-10-01T22:36:39Z [implementation] — Domain: release QA and integration repair. Initial lanes preserved as .initial UTF-8 logs/JUnit: default exit 1 (5 failed, 12783 passed, 34 skipped, 143 deselected); slow exit 1 (1 failed, 142 passed, 0 skipped, 12822 deselected). Ownership: Terra worker fixes compact verifier verdict source plus consumer expectation; Sol bounded packet fixes mypy/canonical signatures in four files; this owner fixes cold-start task-linked decision handoff and existing drill; root corrects stale memory via canonical service. No worker starts a task or reruns lanes. Reruns wait for targeted fixes, one scoped QA verify, then owner runs default and slow sequentially through UTF-8 Python subprocess binary capture.
- 2026-10-01T22:37:10Z [implementation] — AC-8 repair: edited canonical memory #834 to remove the fictitious pytest placeholder path while preserving the dead-end lesson and identity. Exported tausik/memory/first-live-compound-closure-used-test-counts-and-file-names.md now refers to an existing-test citation requirement without inventing a path. Existing repo-hygiene ratchet will verify no stale references; no threshold changed.
- 2026-10-01T22:37:11Z [implementation] — Cold-start repair implemented: handoff decisions include records attached to an active task across a replacement-session boundary while project-wide decisions remain window-bounded. Existing isolated drill now asserts the exact retained task-linked decision, with no sleep or timestamp dependence. Targeted test is intentionally deferred until all assigned integration edits are quiescent.
- 2026-10-01T22:38:28Z [implementation] — Cold-start regression strengthened without sleep: fixture sets the task-linked and unrelated decisions to 2026-01-01 and replacement session start to 2026-01-02. Old window-only logic deterministically omits the required task decision; repaired logic keeps only the active-task decision and excludes the unrelated older record.
- 2026-10-01T22:40:47Z [implementation] — Targeted integration validation PASS: 49 passed across cold-start, mypy, compact-verdict, and hygiene suites; slow consumer PASS: 5 passed; python -m mypy PASS: 544 source files. The actual canonical memory export path was added to QA scope. No duplicate per-owner runs were used.
- 2026-10-01T22:41:47Z [implementation] — Missing untracked canonical path was added before verify: tests/test_task_progress_close.py PASS (11); aligned tests/test_work_packet.py and tests/test_ow_delegate.py PASS (32). Earlier shared targeted results remain PASS: 49 affected default tests, 5 slow consumer tests, and mypy on 544 files. Scoped QA verify is now authorized; no full lane rerun precedes it.
- 2026-10-01T22:54:48Z [implementation] — Default lane complete. Initial red artifacts preserved: 5 failed, 12783 passed, 34 skipped, 143 deselected. UTF-8 rerun exited 0: 12788 passed, 34 skipped, 143 deselected; JUnit tests 12822, failures 0, errors 0, skipped 34; 2026-10-01T22:46:15Z.
- 2026-10-01T22:54:49Z [implementation] — Slow lane complete. Initial red artifacts preserved: 1 failed, 142 passed, 0 skipped, 12822 deselected. UTF-8 rerun exited 0: 143 passed, 0 skipped, 12822 deselected; JUnit tests 143, failures 0, errors 0, skipped 0; 2026-10-01T22:49:19Z.
- 2026-10-01T22:55:13Z [implementation] — Final QA report: commands were python -m pytest -q --junitxml for default and python -m pytest -q -m slow --junitxml for slow. Initial and rerun logs plus JUnit are under .tausik/verification/r111-release-quality-lanes-*. Default rerun 12788 passed, 34 skipped, 143 deselected; slow rerun 143 passed, 0 skipped, 12822 deselected. Route was Codex Terra Medium Standard. Sol and Terra worker edits occurred outside the root native window, so no causal model or complete single-window cost claim is made.
- 2026-10-01T22:55:51Z [implementation] — AC verified: 1. ✓ default.initial.log/JUnit: 5 failed, 12783 passed, 34 skipped, 143 deselected 2. ✓ slow.initial.log/JUnit: 1 failed, 142 passed, 0 skipped, 12822 deselected 3. ✓ UTF-8 reruns: default 12788 passed, 34 skipped, 143 deselected; slow 143 passed, 0 skipped, 12822 deselected 4. ✓ task log names commands, artifacts, timestamps, route, and worker attribution limit 5. ✓ tests/test_cold_start_drill.py::test_isolated_drill_restores_state_then_invalidates_stale_green 6. ✓ tests/test_mypy_clean.py::test_declared_tree_is_mypy_clean; 544 files 7. ✓ tests/test_verify_summary_honesty.py::TestSingleSpellingIsEnforced::test_no_module_spells_the_gate_verdict_itself; slow consumer 5 passed 8. ✓ tests/test_repo_hygiene_ratchet.py::test_stale_memory_refs_within_the_ratchet; canonical memory 834
