---
slug: move-the-flat-scripts-runtime-into-a-2-0-python
title: "Move the flat scripts runtime into a 2.0 Python package"
status: planning
epic: null
story: null
complexity: complex
role: null
stack: null
tier: null
call_budget: null
defect_of: null
scope: "2.0 runtime package layout and compatibility entry points"
scope_exclude: "No physical move during 1.11 release preparation; no commit, push or release"
relevant_files: []
scope_paths: []
scope_tools: []
depends_on:
  - document-the-2-0-package-architecture-and
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

Move the flat scripts runtime into cohesive packages for backend, service, CLI, gates, skills, metrics and providers while preserving thin 1.11 compatibility entry points during the transition.

## Acceptance Criteria

AC-1 Runtime domains have documented package ownership and dependency direction. AC-2 Bootstrap and MCP import the installed package instead of injecting a flat scripts directory into sys.path. AC-3 Compatibility entry points cover the declared 1.11 transition window. AC-4 Tests and deployed profiles use the same package tree. Negative: no second implementation or permanent mirror is created.

## Plan

## Rollback

Restore flat imports and bootstrap copy paths from version control

## Journal
