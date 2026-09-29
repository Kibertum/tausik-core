---
slug: answer-rules-remeasured-after-three-sessions
title: "The answer measure is re-read three sessions after the rules reach every prompt"
status: planning
epic: release-110-deferred-from-19
story: deferred-110-audit-hygiene
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths:
  - "tausik/gates.json"
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

Split from answer-rules-are-in-every-prompt-not-only-consumers (1.10): the injection shipped in session #279; its effect needs sessions. Baseline on the new measure: median 162, p90 365 (newest 10 transcripts).

## Acceptance Criteria

AC-1 After 3 sessions, 'tausik metrics answers' is logged against 162/365. AC-2 NEGATIVE: if it grew, the ratchet's warn is reported, not the baseline moved. AC-3 If it shrank, the baseline in tausik/gates.json is lowered with provenance.

## Plan

## Rollback

git revert

## Journal
