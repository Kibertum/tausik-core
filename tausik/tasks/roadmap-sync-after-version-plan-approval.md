---
slug: roadmap-sync-after-version-plan-approval
title: "reconcile public roadmap after owner approves the version plan"
status: done
epic: release-111-economy-draft
story: release111-administration
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 60
defect_of: null
scope: "docs/ru/research/release-111-economy-plan-2026-10-01.md; ROADMAP.md generated via doc roadmap; TAUSIK planning/decision/task records; .tausik/planning/release-111; approved GitHub issue and milestone metadata"
scope_exclude: "Production implementation; git commit/push; GitLab comments/closures; unrelated external repositories"
relevant_files:
  - "docs/ru/research/release-111-economy-plan-2026-10-01.md"
  - ROADMAP.md
scope_paths:
  - "docs/ru/research/release-111-economy-plan-2026-10-01.md"
  - ROADMAP.md
  - "tausik/"
  - "changelog.d/"
  - ".tausik/planning/release-111/"
scope_tools: []
depends_on: []
completed_at: "2026-10-01T18:50:31Z"
resolution: null
resolution_reason: null
tracker_refs: []
started_model_id: claude-opus-5
started_model_version: null
done_model_id: claude-opus-5
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
---

## Goal

After explicit owner approval in this conversation, apply the reviewed GitHub issue/milestone mapping and reconcile local release composition without silently closing promises or changing scope.

## Acceptance Criteria

AC-1 Read and match the owner's approval to the exact report and tracker-change manifest; re-fetch issues and reject conflicting changes rather than overwriting them. AC-2 Create approved milestones, update descriptions and issue assignments/body links; preserve identifiers, discussion and completed history; repair #194 text from a readable approved reconstruction. AC-3 Reuse #193 for telemetry, create only missing approved task/epic issues, and produce before/after counts with no unmapped approved task. AC-4 Negative: no remote edits or issue closures before approval; no closure based solely on moving a milestone. GitLab #10 follow-up/closure is a separate explicitly listed action requiring evidence and authorization. AC-5 Local composition decision and generated roadmap are updated from approved task membership, not by hand-editing generated ROADMAP.md; rollback manifest records old values.

## Plan

[{"step": "Validate owner approval and refresh/diff the saved issue snapshot.", "done": true}, {"step": "Apply only approved local composition and external roadmap changes with recorded old/new values.", "done": true}, {"step": "Read back and check counts/links; report exceptions without silently broadening the approved change set.", "done": true}]

## Rollback

Revert this task's isolated changes and retain baseline behavior; for data changes use tested backup/restore or reversible migration.

## Journal

- 2026-10-01T15:04:16Z [implementation] — AC-1 ✓ owner approval recorded as decision #410; refreshed GitHub snapshot has 85 issues, no changed/new/missing records. Applied version allocation locally. Product composition is 13 tasks; admin moved outside it. Explicit scope ACL/relevant-files fields set via CLI (not exposed by MCP). task next now selects r111-runtime-observation-contract under release 1.11. GitLab unchanged.
- 2026-10-01T15:06:17Z [implementation] — GitHub sync began: milestone descriptions updated and 1.12/1.13 created with rollback snapshots. Stopped on a failed GET of issue #194 before issue mutation; inspecting transport error and resuming idempotently from the recorded action log. No issue closures.
- 2026-10-01T15:07:10Z [implementation] — Verify #3227 recorded, not green: bootstrap_drift in six deployed tausik_version.py copies; pytest not run. Scope also lacked newly moved planning projections. No gate disabled and no unrelated version/host files changed. Planning validation remains separate; formal closure will require scope expansion and resolving the pre-existing/concurrent deployment drift. GitHub GET connectivity recovered; resume idempotent sync.
- 2026-10-01T15:13:44Z [implementation] — AC verification: approved composition #410/#411 applied. GitHub readback validates all 85 original allocations; 96 open issues now, v1.11=16 (13 product + 3 groups), v1.12=23, v1.13=13, v2.0=34, Planning=8, v1.10=2. All 13 product tracker refs saved via CLI. Durable before/after journal has 68 operations; no GitLab edits/issue closure/commit/push. Plan checks passed; formal closure remains blocked by verify #3227 (scope-narrower-than-diff and bootstrap_drift); no gate waiver. Report updated with evidence and limitation.
- 2026-10-01T18:50:26Z [review] — AC-1: ✓ Decision #410 matches the saved manifest; refreshed snapshot reported no conflicting records. AC-2: ✓ .tausik/planning/release-111/github-readback-validation.json validates milestone descriptions and issue assignments after the approved sync. AC-3: ✓ readback counts 96 open issues and all 13 product tracker refs; #193 was reused. AC-4: ✓ no issue closure, GitLab mutation, commit or push occurred. AC-5: ✓ ROADMAP.md was regenerated by the project command after the approved local composition. Domain: the remote readback validated all 85 original allocations and the newly approved roadmap objects. Negative: GitLab #10 remains separate and untouched; moving a milestone never closed an issue.
