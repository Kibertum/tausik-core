---
slug: roadmap-reissue-blocks-a-fileless-close
title: "A status change reissues ROADMAP.md, and the reissued file then refuses a --no-file-changes close"
status: planning
epic: release-110-deferred-from-19
story: release110-owner-priorities
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
  - "scripts/"
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

Session #279: task unblock rewrote ROADMAP.md (counters moved), and task done --no-file-changes then refused because git saw ROADMAP.md modified. The fileless-close exclusion covers tausik/{tasks,...} projections but not the generated ROADMAP.md, so any status change before a fileless close forces a commit.

## Acceptance Criteria

AC-1 A ROADMAP.md change produced only by the generator does not refuse a fileless close. AC-2 NEGATIVE: a hand edit to ROADMAP.md still refuses it. AC-3 Test covers both.

## Plan

## Rollback

git revert

## Journal
