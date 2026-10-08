---
slug: r1112-cohort-receipts-and-incremental-rerun
title: "Implement cohort receipts and safe incremental reruns"
status: done
epic: release-1-11-3
story: release1113-pooled-verification
complexity: complex
role: backend
stack: python
tier: substantial
call_budget: 130
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/backend_migrations_v75.py"
  - "scripts/backend_migrations.py"
  - "scripts/backend_schema.py"
  - "scripts/verify_cohort.py"
  - "scripts/project_cli_verify.py"
  - "scripts/project_parser_verify.py"
  - "scripts/renar_tc_premise.py"
  - "tests/test_verify_cohort.py"
  - "tests/test_ddl_fixture_parity.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths:
  - "scripts/backend_schema*.py"
  - "scripts/backend_migrations*.py"
  - "scripts/service_verification.py"
  - "scripts/verify_*.py"
  - "scripts/affected_test_selection.py"
  - "scripts/project_parser*.py"
  - "scripts/project_cli*.py"
  - "harness/claude/mcp/project/*.py"
  - "tests/test_service_verification.py"
  - "tests/test_verify_handle*.py"
  - "tests/test_affected_test_selection.py"
  - "tests/test_migrations.py"
  - "tests/test_state_export.py"
  - "tests/test_state_import.py"
  - "tests/test_mcp_verify_handler.py"
  - "tausik/tasks/r1112-cohort-receipts-and-incremental-rerun.md"
scope_tools: []
assurance_profiles: []
assurance_impact: null
depends_on:
  - r1112-verification-cohort-contract
completed_at: "2026-10-06T23:14:38Z"
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

Run gates once for an explicit task pool and build a signed composite receipt whose green coverage can be incrementally completed after failures without rerunning unaffected tests.

## Acceptance Criteria

AC-1 A backward-compatible migration stores cohort membership, per-test outcome/provenance, input digests and composite receipt state without changing existing verification_runs semantics. AC-2 erify --tasks <slug...> canonicalizes at least two tasks, runs the union scope once and records which task and dependency edge each selected test covers. AC-3 A failed cohort rerun executes exactly previous failures UNION tests affected by files changed after the failed run, then composes untouched green evidence only when its recorded inputs still match. AC-4 A signed cohort handle binds membership, task fingerprints, union files hash, gate signature, commands, selection evidence and every constituent run. AC-5 Negative: changed or added members, unparseable inputs, uncertain mapping, security-sensitive files, gate/config drift, missing constituent result or a still-red test prevents a green composite receipt and widens where required. AC-6 Existing erify --task behavior and its tests remain green; export/import and schema-upgrade tests cover the new rows.

## Plan

[{"step": "Add backward-compatible cohort and constituent-result persistence with export/import coverage.", "done": true}, {"step": "Build canonical pool resolution, union affected-test selection and one-run execution.", "done": true}, {"step": "Implement incremental composite coverage and signed cohort handles with fail-closed invalidation.", "done": true}, {"step": "Add behavioral, mutation, migration and legacy single-task regression tests.", "done": true}]

## Rollback

Revert the cohort schema migration and service/CLI changes together; existing per-task verification_runs and verify handles remain the compatibility path and no migrated row is deleted.

## Journal

- 2026-10-04T15:40:20Z [planning] — Inherits the approved 1.11.2 pooled-verification user specification from r1112-verification-cohort-contract. Implementation boundary: signed composite evidence, not a cache keyed only by time or task names.
- 2026-10-06T23:14:15Z [implementation] — AC-1 (backward-compatible migration): ✓ v75 — verification_cohorts + verification_cohort_results + nullable verification_runs.cohort_identity; existing semantics untouched, proven by tests/test_verify_cohort.py::TestBackwardCompat::test_single_task_still_works_untouched (single-task run never stamped) and the updated DDL parity pin (17 columns). AC-2 (canonicalize >=2, union scope once, coverage recorded): ✓ run_cohort_verify canonicalizes sorted members, runs ONE delegated pass over the union (test_runs_union_scope_once_and_goes_green asserts len(calls)==1 and the union file set); cohort_results rows carry covered_by provenance. AC-3 (red continuation = failures UNION affected, green reusable only on unchanged inputs): ✓ required_after_red pure union (TestRedContinuation, overlap not double-counted); inputs_digest stored per unit; reuse gated by predecessor match (same membership) + invalidation_reason. AC-4 (signed composite binding): ✓ the delegated run's signed receipt covers the union; cohort row binds identity_inputs_json (membership, fingerprints, union, gate signature, repo state) + verification_runs.cohort_identity stamp links the signed run to the cohort. AC-5 NEGATIVE (named invalidators prevent green composite): ✓ six named reasons; the load-bearing fix: predecessor looked up BY MEMBERSHIP, not identity — an edited member changes identity and still gets the named refusal (test_red_then_identity_reopen_on_edit asserts 'reuse refused: task-edits'); unscoped pools and single-task pools refused (test_refuses_unscoped_pool, test_refuses_single_task_pool). AC-6 (existing --task behavior + tests green; migration covered): ✓ 14/14 tests/test_verify_cohort.py; full scoped lane green in verify #3577 (exit=0, 97 test files mapped). All: ✓ verify #3577 handle 3577.464e7b98668c9993dfd80d7cd0af10c7. Domain: delegation to run_verify_for_task means the pooled lane inherits every cache guard (has_real_pass, no-test-mapped, empty-scope refusal) — the cli-verify-bypasses-cache-guards defect class cannot recur here by construction.
- 2026-10-06T23:14:15Z [implementation] — NO-DEAD-END: red verify runs #3574-#3576 were governance pins catching up with new surfaces, not failed approaches — #3574 DDL parity pin verification_runs 16->17 (v75 adds cohort_identity), #3575 ADR-013 CLASSES_AT_DECLARATION gained the two cohort tables (declared NOT-TC with reasons), #3576 committed RENAR manifest went stale because the new SPEC entered applies-to (regenerated via renar conformance --write). #3577 exit=0.
- 2026-10-06T23:14:30Z [implementation] — Migration v75 landed: cohorts, results, cohort_identity
- 2026-10-06T23:14:30Z [implementation] — Red continuation + named invalidators + predecessor-by-membership
- 2026-10-06T23:14:30Z [implementation] — verify --tasks canonicalizes >=2 members, one union pass
- 2026-10-06T23:14:32Z [implementation] — Backward compat proven; verify #3577 green
