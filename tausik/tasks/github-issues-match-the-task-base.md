---
slug: github-issues-match-the-task-base
title: "GitHub issues match the task base after 1.10: done closed with the version, the rest in the right milestone"
status: active
epic: release-110-deferred-from-19
story: release110-owner-priorities
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
  - "tausik/"
  - "docs/"
scope_tools: []
depends_on: []
completed_at: null
resolution: null
resolution_reason: null
tracker_refs: []
started_model_id: claude-opus-5
started_model_version: null
done_model_id: null
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
---

## Goal

Owner, session #279: tidy the GitHub tracker. Every open issue is mapped to its task (tracker_refs github#N): a done task closes its issue with a comment naming 1.10.0; an open task sits in the milestone of its story (1.10 composition -> v1.10.0, deferred -> v1.11.0, 2.0 -> v2.0.0); an epic closes when every child is done; an issue with no task is listed, not guessed at.

## Acceptance Criteria

AC-1 The full mapping (issue -> task -> action) is logged before anything is changed. AC-2 After the release is on GitHub, done issues are closed with a comment naming 1.10.0 and the release link. AC-3 Open issues sit in the milestone of their task's release. AC-4 NEGATIVE: an issue with no linked task is not closed or moved by guess; it is listed for the owner. AC-5 NEGATIVE: nothing outside Kibertum/tausik-core is touched.

## Plan

## Rollback

Reopen the closed issues and restore milestones from the list logged in the task

## Journal
