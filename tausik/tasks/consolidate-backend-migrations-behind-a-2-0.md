---
slug: consolidate-backend-migrations-behind-a-2-0
title: "Consolidate backend migrations behind a 2.0 baseline"
status: planning
epic: null
story: null
complexity: complex
role: null
stack: null
tier: null
call_budget: null
defect_of: null
scope: "2.0 migration baseline and supported upgrade bridge"
scope_exclude: "Not before 1.11 release; no commit, push or release"
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

After 1.11 ships and the minimum supported source schema is declared, replace the v2-v67 module fan-out with a tested baseline plus the smallest supported upgrade bridge.

## Acceptance Criteria

AC-1 The minimum supported source schema is explicit. AC-2 Fresh 2.0 databases use one canonical schema baseline. AC-3 Every supported 1.11 database upgrades with data and indexes intact. AC-4 Historical migrations outside the support window leave the runtime import path. Negative: 1.11.x databases are never silently abandoned.

## Plan

## Rollback

Restore the v2-v67 migration registry and modules from version control

## Journal
