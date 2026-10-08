---
slug: r1112-verification-cohort-contract
title: "Define the pooled-verification safety contract"
status: done
epic: release-1-11-3
story: release1113-pooled-verification
complexity: medium
role: architect
stack: python
tier: moderate
call_budget: 45
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/verify_baseline.py"
  - "tests/test_verify_baseline.py"
  - "docs/en/verification-cohort-contract.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths:
  - "docs/en/research/release1112-pooled-verification.md"
  - "docs/ru/research/release1112-pooled-verification.md"
  - "docs/en/receipts.md"
  - "docs/ru/receipts.md"
  - "tausik/tasks/r1112-verification-cohort-contract.md"
scope_tools: []
assurance_profiles: []
assurance_impact: null
depends_on: []
completed_at: "2026-10-06T22:51:52Z"
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

Measure the current repeated-verify cost and define an implementable cohort identity, lifecycle and invalidation contract that saves duplicate regression runs without accepting stale green evidence.

## Acceptance Criteria

AC-1 A reproducible baseline reports verify invocations, selected/full fallback reasons and elapsed time for cohorts of 1, 2 and at least 5 tasks. AC-2 The spec defines canonical cohort identity from sorted task membership, task fingerprints, union scope, content hashes, gate signature, selected tests and repository state. AC-3 Tasks must be review-ready with complete plan and AC evidence before entering a close cohort; story/epic closure is atomic. AC-4 After a red run, the next required set is previous failures UNION tests affected by files changed since that run; prior green results are reusable only when their dependency inputs are unchanged. AC-5 Negative: membership drift, task edits, config or gate-signature drift, security-sensitive scope, uncertain dependency mapping or missing evidence invalidates reuse or widens to the full applicable lane. AC-6 The schema/API migration and backward-compatibility plan preserves existing single-task verify and signed-handle behavior.

## Plan

[{"step": "Measure current single-task and repeated multi-task verify behavior, including why selection widens.", "done": true}, {"step": "Specify cohort membership, readiness, hashes, receipt lifecycle and atomic closure semantics.", "done": true}, {"step": "Specify safe red-run continuation as failures union affected-by-delta, with full-lane invalidation boundaries.", "done": true}, {"step": "Review the contract against SENAR QG-2, backward compatibility and migration constraints.", "done": true}]

## Rollback

This task changes only the specification and planning records; revert its documentation commit and leave the existing per-task verify path unchanged.

## Journal

- 2026-10-04T15:40:20Z [planning] — User specification (2026-10-04): 1. Target release is 1.11.2; the 1.x line has no 1.12+, and the next non-patch release is 2.0. 2. When more than one task is intended to close together, first bring every task to a state where only final verification remains. 3. Run one shared regression for the exact task pool, preferably at story or epic closure when hierarchy exists. 4. Do not repeat the same green work for the unchanged pool. After a red run, execute previous failures plus tests affected by subsequent edits; never carry green evidence across an unsafe change. 5. Optimize elapsed development time without weakening QG-2 or hiding denominators.
- 2026-10-06T22:51:06Z [implementation] — NO-DEAD-END: red verify runs #3569-#3571 were gate iterations on the new doc page — missing doc-map declaration, zone outside the closed list (verification -> quality), stale generated map (regenerated via scripts/doc_map.py --write). #3572 exit=0.
- 2026-10-06T22:51:16Z [implementation] — AC-1 (reproducible baseline, cohorts 1/2/5+): ✓ scripts/verify_baseline.py — live: cohort-of-1: 51 cohorts/134 invocations/2169s; cohort-of-2: 24/48 tasks/109 invocations/1801.9s; cohort-of-5+: 64 cohorts/784 tasks/2049 invocations/45056.9s (~12.5h), fallback reasons enumerated (under-declared 1175 dominates 5+); aggregate: 3562 runs/1409 tasks, 2153 duplicate invocations = 60.4%, 1076 tasks re-run, 248 red at least once; tests/test_verify_baseline.py 2 passed (bucketing + empty DB). AC-2 (canonical identity): ✓ SPEC verification-cohort-contract ARCH 1.0-draft, docs/en/verification-cohort-contract.md §1 — sorted membership, task fingerprints, union scope, content hashes, gate signature, selected tests, repository state, SHA-256 over canonical serialization. AC-3 (review-ready + atomic closure): ✓ §2 lifecycle. AC-4 (red -> failures UNION affected): ✓ §3. AC-5 NEGATIVE (named invalidators widen to full lane): ✓ §4 — six, each refusal names which fired. AC-6 (schema/API migration, backward compat): ✓ §5 — nullable cohort columns, single-task verify + signed handles unchanged. All: ✓ green verification_run #3572, SPEC linked (implements). Domain: numbers read from the production verification_runs table; contract drafted against the real gate surface it will constrain.
- 2026-10-06T22:51:46Z [implementation] — Baseline measured and reproducible (60.4% duplicate invocations; 12.5h in 5+ cohorts)
- 2026-10-06T22:51:46Z [implementation] — Cohort identity contract drafted (SPEC ARCH 1.0-draft)
- 2026-10-06T22:51:47Z [implementation] — Lifecycle, red-handling, invalidators specified
- 2026-10-06T22:51:47Z [implementation] — Migration plan; SPEC linked; verify #3572 green
