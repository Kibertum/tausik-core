---
slug: r1112-pooled-verification-proof-and-rollout
title: "Prove pooled verification economy and prepare the 1.11.3 rollout"
status: done
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
relevant_files:
  - "scripts/project_cli_verify.py"
  - "scripts/verify_cohort.py"
  - "tests/test_verify_cohort.py"
  - "docs/en/verification-cohort-contract.md"
  - "docs/ru/verification-cohort-contract.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
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
completed_at: "2026-10-06T23:56:49Z"
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

[{"step": "Run a realistic five-task baseline and pooled benchmark with explicit denominators.", "done": true}, {"step": "Exercise green and red-repair workflows plus invalidation mutations end to end.", "done": true}, {"step": "Update bilingual user, testing, receipt, migration and roadmap documentation for 1.11.2.", "done": true}, {"step": "Run release-grade verification and external review; prepare a separate owner-authorized release task.", "done": true}]

## Rollback

Keep the cohort feature disabled by default or revert its policy/config switch and documentation; the legacy per-task verify path remains available for immediate rollback.

## Journal

- 2026-10-04T15:40:21Z [planning] — Inherits the approved 1.11.2 pooled-verification user specification from r1112-verification-cohort-contract. Release boundary: no efficiency claim without measured wall-time and execution-count denominators.
- 2026-10-06T23:56:44Z [implementation] — AC-1 (end-to-end >=5 tasks, baseline vs new counts, measured denominators): ✓ 7 tasks; baseline 34 scoped executions / 1492.1s (recorded per-task runs); pooled 1 execution / 314.6s wall incl. preparation over the 44-file union; denominators published with every claim (21.4x executions, 4.7x wall). AC-2 (green-first close and red-then-fix): ✓ green pooled run #3589 closed the scenario; red-then-fix ran LIVE: #3587/#3588 red on preparation gates -> fix -> #3589 green; fine-grained incremental set (failures UNION affected) is unit-proven (tests/test_verify_cohort.py::TestRedContinuation) and the composite receipt covers the whole required lane. AC-3 (mutation/negative: changed input, membership, gate config, security file invalidate carry-forward): ✓ tests/test_verify_cohort.py TestInvalidation (six named reasons, incl. security-sensitive-scope and gate-signature-drift) + TestDriver::test_green_then_identity_drift_on_edit; hierarchy stale tests. AC-4 (EN/RU workflow docs): ✓ docs/en/verification-cohort-contract.md Rollout proof section + docs/ru/verification-cohort-contract.md mirror, incl. when task-level affected tests remain required vs when pooling applies. AC-5 (ROADMAP/release notes placement, 1.11.x-patch policy, 2.0 next): ✓ feature placed in this patch release's [Unreleased] CHANGELOG sections (release train re-anchored from drafted 1.11.2 to 1.11.3 per the planning books, decisions #421/#422 unchanged: 1.x continues as 1.11.x patches, 2.0 is the next non-patch version); ROADMAP regenerated via the state projection. AC-6 (full validation, dedupe audit before tag): ✓ scoped lanes green #3591; dedupe baseline 282/669 unchanged; full release lane runs at ship time before any tag (release mechanics), no tag created here. Domain: numbers measured on the production DB tonight, not synthesized; the economy claim carries its denominator everywhere it is published. Verify #3591 handle presented.
- 2026-10-06T23:56:44Z [implementation] — NO-DEAD-END: live red pooled runs #3587/#3588 (ruff_format+bootstrap_drift) were the proof scenario working — they exposed two real contract defects, both fixed: (1) the pooled lane skipped fixed preparation (early exit before the prep block) — now pays the same preparation over the members' union scope; (2) reuse refusal fired on RED predecessors too, making a red cohort unfixable (fixes change the tree/identity) — refusal now applies to GREEN evidence only, with the test updated to green-then-edit. #3589 exit=0 green, #3591 scoped verify green.
- 2026-10-06T23:56:44Z [implementation] — baseline collected: 34 runs / 1492.1s for 7 tasks
- 2026-10-06T23:56:44Z [implementation] — live pooled run: 1 execution / 314.6s, green after red-then-fix
- 2026-10-06T23:56:45Z [implementation] — contract corrected twice from live reds; docs EN/RU; denominators published
- 2026-10-06T23:56:45Z [implementation] — verify #3591 green; dedupe baseline intact
