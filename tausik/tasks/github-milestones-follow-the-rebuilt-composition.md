---
slug: github-milestones-follow-the-rebuilt-composition
title: "GitHub milestones and tickets follow the rebuilt 1.10 composition"
status: active
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
  - "docs/"
  - "changelog.d/"
  - "tausik/"
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

Owner, session #279: before the release, GitHub milestones/tickets must match decision #408. Tickets of tasks moved to 1.11 carry the 1.10 milestone; new 1.10 tasks may have no ticket.

## Acceptance Criteria

AC-1 Every open GitHub issue in milestone 1.10 is mapped to a task in the #408 composition or moved to milestone 1.11 (list logged before and after). AC-2 NEGATIVE: no issue is closed or edited beyond its milestone without the owner. AC-3 The change list is shown to the owner before it is applied (outward action).

## Plan

## Rollback

re-assign milestones back from the logged list

## Journal

- 2026-09-29T22:16:01Z [implementation] — AC-1 mapping (read-only, gh api, 2026-09-30): milestone v1.10.0 has 93 open issues: 83 map to tasks already DONE (issues stay open until the release closes them), 1 to the blocked site task (#189), 9 are epics with no task link — nothing to move out. PROPOSED (not applied): #143 v1.11.0 -> v1.10.0 (context-order, done in 1.10); #118 v1.11.0 -> v1.10.0 (demo, done in 1.10); #95 v1.11.0 -> v1.10.0 (we-say, in #408 composition, blocked on the owner); #120 Planning -> v1.10.0 (verify-first profile, closed obsolete in 1.10 — resolved, not dropped). #125 stays v1.11.0 (memory-tail moved out of 1.10). 12 new 1.10 tasks carry no ticket; none needed for the milestone. AC-2: nothing closed or edited.
- 2026-09-29T22:29:38Z [implementation] — AC-3: ✓ owner approved in session #279 ('2. Да'). Applied via gh api PATCH: #143 -> v1.10.0, #118 -> v1.10.0, #95 -> v1.10.0, #120 -> v1.10.0 (each confirmed by the API response). AC-1: ✓ mapping logged earlier (83 done, 1 blocked site, 9 epics, 4 moved). AC-2 Negative: ✓ no issue closed or edited beyond its milestone.
