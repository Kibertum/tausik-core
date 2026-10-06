---
slug: r1112-cohort-receipts-and-incremental-rerun
title: "Implement cohort receipts and safe incremental reruns"
status: planning
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
relevant_files: []
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

Run gates once for an explicit task pool and build a signed composite receipt whose green coverage can be incrementally completed after failures without rerunning unaffected tests.

## Acceptance Criteria

AC-1 A backward-compatible migration stores cohort membership, per-test outcome/provenance, input digests and composite receipt state without changing existing verification_runs semantics. AC-2 erify --tasks <slug...> canonicalizes at least two tasks, runs the union scope once and records which task and dependency edge each selected test covers. AC-3 A failed cohort rerun executes exactly previous failures UNION tests affected by files changed after the failed run, then composes untouched green evidence only when its recorded inputs still match. AC-4 A signed cohort handle binds membership, task fingerprints, union files hash, gate signature, commands, selection evidence and every constituent run. AC-5 Negative: changed or added members, unparseable inputs, uncertain mapping, security-sensitive files, gate/config drift, missing constituent result or a still-red test prevents a green composite receipt and widens where required. AC-6 Existing erify --task behavior and its tests remain green; export/import and schema-upgrade tests cover the new rows.

## Plan

[{"step": "Add backward-compatible cohort and constituent-result persistence with export/import coverage.", "done": false}, {"step": "Build canonical pool resolution, union affected-test selection and one-run execution.", "done": false}, {"step": "Implement incremental composite coverage and signed cohort handles with fail-closed invalidation.", "done": false}, {"step": "Add behavioral, mutation, migration and legacy single-task regression tests.", "done": false}]

## Rollback

Revert the cohort schema migration and service/CLI changes together; existing per-task verification_runs and verify handles remain the compatibility path and no migrated row is deleted.

## Journal

- 2026-10-04T15:40:20Z [planning] — Inherits the approved 1.11.2 pooled-verification user specification from r1112-verification-cohort-contract. Implementation boundary: signed composite evidence, not a cache keyed only by time or task names.
