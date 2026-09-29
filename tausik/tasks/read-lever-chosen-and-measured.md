---
slug: read-lever-chosen-and-measured
title: "A lever for the read category is chosen from metrics calls and measured before/after"
status: planning
epic: release-110-deferred-from-19
story: deferred-110-audit-hygiene
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths:
  - "scripts/"
  - "harness/"
  - "docs/"
  - "tests/"
  - "changelog.d/"
scope_tools: []
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

Split from reading-code-costs-a-third-of-calls (1.10): the measurement shipped; the lever needs sessions. BEFORE (session #279, newest 10 transcripts, 198 closed tasks): median calls simple 14 (read 2), medium 29 (read 7), complex 50 (read 18); read 30.8% of attributed calls.

## Acceptance Criteria

AC-1 One lever for the read category is chosen from 'tausik metrics calls' and shipped. AC-2 After 3+ sessions, calls per task by complexity are re-measured and logged against BEFORE. AC-3 NEGATIVE: if the read median does not fall, it is said and the lever is reverted or kept with a reason.

## Plan

## Rollback

git revert

## Journal
