---
slug: r1112-hierarchy-verify-and-atomic-close
title: "Close story and epic cohorts atomically from one receipt"
status: planning
epic: release-1-11-3
story: release1113-pooled-verification
complexity: complex
role: backend
stack: python
tier: substantial
call_budget: 110
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths:
  - "scripts/service_hierarchy.py"
  - "scripts/service_task*.py"
  - "scripts/project_parser*.py"
  - "scripts/project_cli*.py"
  - "scripts/verify_*.py"
  - "scripts/backend_*.py"
  - "harness/claude/mcp/project/*.py"
  - "tests/test_hierarchy_update.py"
  - "tests/test_project_mcp.py"
  - "tests/test_verify_handle*.py"
  - "tests/test_tausik_service.py"
  - "tests/test_consumer_first_close.py"
  - "tausik/tasks/r1112-hierarchy-verify-and-atomic-close.md"
scope_tools: []
assurance_profiles: []
assurance_impact: null
depends_on:
  - r1112-cohort-receipts-and-incremental-rerun
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

Let story and epic closure consume one exact cohort receipt and atomically close all review-ready descendants, while leaving standalone task closure compatible.

## Acceptance Criteria

AC-1 erify --story <slug> and erify --epic <slug> resolve the exact non-done descendant task set and refuse an empty or single-task cohort unless explicitly requested as ordinary task verify. AC-2 Eligibility requires every member to be review-ready, all plan steps complete and numbered AC evidence present before the cohort run starts. AC-3 story done --verify-handle and epic done --verify-handle validate the exact cohort and close member tasks plus parent hierarchy atomically without rerunning gates. AC-4 Negative: a task added, removed, edited, reopened or made blocked after verify makes the handle stale; partial closure rolls back the transaction. AC-5 Standalone 	ask done and single-task handles keep their current contract; hierarchy use is opt-in and no task loses its own evidence trail. AC-6 CLI and MCP expose parity, bounded progress and an explicit denominator: members, test files, passed, failed, carried-forward, skipped and deselected.

## Plan

[{"step": "Resolve eligible story and epic descendants and surface readiness failures before running tests.", "done": false}, {"step": "Expose story/epic cohort verification through service, CLI and MCP with bounded progress.", "done": false}, {"step": "Consume exact cohort handles in an atomic task-plus-hierarchy closure transaction.", "done": false}, {"step": "Prove stale membership, task edits and partial-failure rollback while preserving standalone closure.", "done": false}]

## Rollback

Revert hierarchy/CLI/MCP integration; cohort receipts remain inert evidence and existing task done, story done and epic done commands retain their pre-1.11.2 behavior.

## Journal

- 2026-10-04T15:40:21Z [planning] — Inherits the approved 1.11.2 pooled-verification user specification from r1112-verification-cohort-contract. Hierarchy boundary: use story/epic when present, preserve standalone tasks when absent.
