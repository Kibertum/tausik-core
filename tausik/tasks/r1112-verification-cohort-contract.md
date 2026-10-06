---
slug: r1112-verification-cohort-contract
title: "Define the pooled-verification safety contract"
status: active
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
relevant_files: []
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
completed_at: null
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

[{"step": "Measure current single-task and repeated multi-task verify behavior, including why selection widens.", "done": false}, {"step": "Specify cohort membership, readiness, hashes, receipt lifecycle and atomic closure semantics.", "done": false}, {"step": "Specify safe red-run continuation as failures union affected-by-delta, with full-lane invalidation boundaries.", "done": false}, {"step": "Review the contract against SENAR QG-2, backward compatibility and migration constraints.", "done": false}]

## Rollback

This task changes only the specification and planning records; revert its documentation commit and leave the existing per-task verify path unchanged.

## Journal

- 2026-10-04T15:40:20Z [planning] — User specification (2026-10-04): 1. Target release is 1.11.2; the 1.x line has no 1.12+, and the next non-patch release is 2.0. 2. When more than one task is intended to close together, first bring every task to a state where only final verification remains. 3. Run one shared regression for the exact task pool, preferably at story or epic closure when hierarchy exists. 4. Do not repeat the same green work for the unchanged pool. After a red run, execute previous failures plus tests affected by subsequent edits; never carry green evidence across an unsafe change. 5. Optimize elapsed development time without weakening QG-2 or hiding denominators.
