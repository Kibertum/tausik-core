---
slug: fix-task-claim-race
title: "Атомарный task_claim"
status: done
epic: hardening
story: bugfixes
complexity: medium
role: developer
stack: null
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-03-14T13:44:06Z"
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

UPDATE WHERE claimed_by IS NULL вместо read-check-write

## Acceptance Criteria

## Plan

## Rollback

## Journal
