---
slug: r1112-pooled-verification-proof-and-rollout
title: "Prove pooled verification economy and prepare the 1.11.3 rollout"
status: planning
epic: release-1-11-3
story: release1113-pooled-verification
complexity: medium
role: developer
stack: python
tier: substantial
call_budget: 70
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths:
  - ROADMAP.md
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - "docs/en/cli-quality.md"
  - "docs/ru/cli-quality.md"
  - "docs/en/receipts.md"
  - "docs/ru/receipts.md"
  - "docs/en/testing-principles.md"
  - "docs/ru/testing-principles.md"
  - "docs/en/workflow.md"
  - "docs/ru/workflow.md"
  - "docs/en/migrations.md"
  - "docs/ru/migrations.md"
  - "tests/test_e2e_workflow.py"
  - "tests/test_docs*.py"
  - "tests/test_release_roadmap.py"
  - "tausik/tasks/r1112-pooled-verification-proof-and-rollout.md"
scope_tools: []
assurance_profiles: []
assurance_impact: null
depends_on:
  - r1112-hierarchy-verify-and-atomic-close
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

Demonstrate that cohort verification removes duplicate full regressions in a realistic multi-task workflow, document its safety boundary, and prepare the feature for patch release 1.11.2.

## Acceptance Criteria

AC-1 An end-to-end scenario with at least five tasks records the baseline and new counts of full-lane executions, incremental executions and wall time; no percentage claim is published without the measured denominator. AC-2 The scenario covers green-first close and red-then-fix: after the first red run only prior failures plus tests affected by later edits execute, while the final composite receipt still accounts for the entire required lane. AC-3 Mutation/negative cases prove that changing a previously green test input, membership, gate config or a security-sensitive file invalidates carry-forward and cannot close the cohort. AC-4 EN/RU workflow, CLI, receipts, testing principles and migration docs explain when task-level affected tests remain required and when story/epic pooling applies. AC-5 ROADMAP and release notes place the feature in 1.11.2, preserve the policy that 1.x continues only as 1.11.x patches, and make 2.0 the next non-patch version. AC-6 Full release validation, dedupe audit and external review pass before any 1.11.2 tag or release is created.

## Plan

[{"step": "Run a realistic five-task baseline and pooled benchmark with explicit denominators.", "done": false}, {"step": "Exercise green and red-repair workflows plus invalidation mutations end to end.", "done": false}, {"step": "Update bilingual user, testing, receipt, migration and roadmap documentation for 1.11.2.", "done": false}, {"step": "Run release-grade verification and external review; prepare a separate owner-authorized release task.", "done": false}]

## Rollback

Keep the cohort feature disabled by default or revert its policy/config switch and documentation; the legacy per-task verify path remains available for immediate rollback.

## Journal

- 2026-10-04T15:40:21Z [planning] — Inherits the approved 1.11.2 pooled-verification user specification from r1112-verification-cohort-contract. Release boundary: no efficiency claim without measured wall-time and execution-count denominators.
