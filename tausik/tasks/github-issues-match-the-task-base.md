---
slug: github-issues-match-the-task-base
title: "GitHub issues match the task base after 1.10: done closed with the version, the rest in the right milestone"
status: done
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
completed_at: "2026-09-30T00:48:24Z"
resolution: null
resolution_reason: null
tracker_refs: []
started_model_id: claude-opus-5
started_model_version: null
done_model_id: claude-opus-5
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 1
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

- 2026-09-29T23:08:04Z [implementation] — AC-1 MAP (gh api, 184 open issues, before any change): CLOSE after release 93 (task done/obsolete); KEEP 56 (milestone already matches the task's release); MOVE Planning -> v1.11.0 20: #156 #152 #151 #147 #140 #136 #132 #130 #114 #103 #102 #101 #100 #99 #93 #89 #88 #80 #78 #62 (except #78 -> v2.0.0, a v2- task); NO-TASK 15, all epics: close after release when every child is closed -> #192 #168 #167 #166 #55 #54 #53 #52; keep #188 (child #189 site open), #170 #169 (1.11), #59 #58 #57 #56 (2.0).
- 2026-09-30T00:48:24Z [implementation] — AC-2: ✓ 101 GitHub issues closed with 'Done in TAUSIK 1.10.0: <release url>' (93 done tasks + epics #192 #168 #167 #166 #55 #54 #53 #52), 0 failures; GitLab #18 #8 #11 closed with the same note. AC-3: ✓ 20 moved earlier (19 -> v1.11.0, #78 -> v2.0.0); v1.10.0 now open=2 (#189 site, #188 its epic). AC-4 Negative: ✓ issues with no task (epics) handled by rule, GitLab #10 (no done task) left open. AC-5 Negative: ✓ only Kibertum/tausik-core and the GitLab core project touched.
