---
slug: prepare-a-cross-host-release-plan-focused-on
title: "Prepare a cross-host release plan focused on Codex economy for 1.11"
status: done
epic: release-111-economy-draft
story: release111-administration
complexity: medium
role: architect
stack: python
tier: moderate
call_budget: 60
defect_of: null
scope: "docs/ru/research/release-111-economy-plan-2026-10-01.md; .tausik/planning/release-111/ local tracker snapshots; draft TAUSIK planning records"
scope_exclude: "Production code, existing uncommitted edits, committed release compositions, remote GitHub/GitLab mutations"
relevant_files:
  - "docs/ru/research/release-111-economy-plan-2026-10-01.md"
scope_paths:
  - "docs/ru/research/release-111-economy-plan-2026-10-01.md"
  - "tausik/"
  - "changelog.d/"
  - ".tausik/planning/release-111/"
scope_tools: []
depends_on: []
completed_at: "2026-10-01T18:50:04Z"
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

Review all open local plans and current GitHub/GitLab issues, draft a versioned task plan with Codex-first and GLM-compatible contracts, and prepare an exact tracker change proposal for owner approval.

## Acceptance Criteria

AC-1 Inventory all open local tasks and current open/recent issues in both configured trackers with access limits stated. AC-2 Draft version assignments with rationale, reused tasks, dependencies, acceptance checks and Codex/GLM host-versus-model boundary. AC-3 Prepare GitHub roadmap change mapping but perform no external tracker mutations before owner approval. AC-4 Negative: do not claim GLM live parity or token savings without measured evidence; preserve existing uncommitted work.

## Plan

[{"step": "Review all open local plans and current GitHub/GitLab issues.", "done": true}, {"step": "Create the versioned draft with universal Codex/GLM contracts, task criteria and dependencies.", "done": true}, {"step": "Validate complete issue/task mapping and present the version plan for owner approval before remote updates.", "done": true}]

## Rollback

Remove only the new draft report and mark newly created draft planning records obsolete; retain original task assignments and all pre-existing changes.

## Journal

- 2026-10-01T14:42:37Z [implementation] — Inventory: GitHub 85 open issues (49 v1.11 candidates, 32 v2.0, 2 v1.10 site, 2 new #193/#194 without milestone), 4 milestone descriptions read; GitLab all 18 issues, only #10 open, recent #8/#11/#18 closed 2026-09-30. API snapshots stored locally under .tausik/planning/release-111. #193 directly matches Codex baseline task; #194 requires live hook capability proof, body/title contain literal '?' corruption. Local snapshot 83 planning/active/blocked tasks including this planning task and a concurrent active release fix. Findings: old 1.11 is candidates, not approved composition; memory-tail #125 requires missing per-record access tracking and layers, so move proposal to 1.12; do not sell it as cheap context reduction. GitLab #10 patch0004 superseded by git-baseline implementation in 1.10; consumer follow-up needed, not duplicate implementation. No remote writes.
- 2026-10-01T14:53:34Z [implementation] — AC-1 ✓ reviewed 83 local open records, 85 GitHub issues and 18 GitLab issues. AC-2 ✓ draft report: docs/ru/research/release-111-economy-plan-2026-10-01.md; 13 product tasks (6 new/7 reused), 960-call estimate, Codex+GLM contracts. AC-3 ✓ exact 48-milestone-change proposal; no remote writes. AC-4 ✓ no production edits or savings/live-parity claims. Validation: 14 records have goal/AC/plan/rollback/budget; dependency graph acyclic; mapping unique/complete. Awaiting owner composition approval.
- 2026-10-01T14:57:14Z [implementation] — Owner clarified primary workflow: Claude Code, Kilo/GLM, Codex. Updated draft report, epic and 10 task AC: all three require live acceptance; Codex remains main economy benchmark. Cursor/OpenRouter share contracts with a combined proposed +25-call compatibility cap; deep integration defers without blocking 1.11. Still 13 product tasks. Validated report encoding and refreshed task manifests. No remote edits; version composition still awaiting approval.
- 2026-10-01T18:49:46Z [review] — AC-1: ✓ tracker snapshots and 83-task inventory recorded in the approved report. AC-2: ✓ 13-task composition, dependencies, budgets and host/model boundary validated. AC-3: ✓ exact roadmap manifest prepared before owner approval. AC-4: ✓ Decision #414 keeps GLM theoretical and the acceptance report makes no 30% claim. Domain: owner approved the exact composition as Decision #410; downstream product tasks are now completed or explicitly blocked with a named live-host prerequisite. Negative: no GitLab mutation, commit or push was performed.
- 2026-10-01T18:49:59Z [review] — NO-DEAD-END: attempt count increased when the owner clarified the host matrix and then approved the plan; the work was resumed and updated, not abandoned after a failed technical approach.
