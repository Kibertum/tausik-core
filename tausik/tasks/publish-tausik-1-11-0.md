---
slug: publish-tausik-1-11-0
title: "Publish TAUSIK 1.11.0"
status: done
epic: null
story: null
complexity: medium
role: null
stack: null
tier: null
call_budget: null
defect_of: null
scope: "Release administration across the already-verified core worktree, GitLab core remote, filtered GitHub public snapshot/release/issues, official three-skill store, and documentation site."
scope_exclude: "No new product features, no force-push, no unrelated repositories, no closure of r111-verification-cycle-replay."
relevant_files:
  - "docs/en/whats-new-1.11.md"
  - "docs/ru/whats-new-1.11.md"
  - "tausik/published_tags.json"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-10-02T17:49:12Z"
resolution: null
resolution_reason: null
tracker_refs: []
started_model_id: gpt-6-astra
started_model_version: null
done_model_id: gpt-6-astra
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 1
token_budget: null
cost_budget_usd: null
---

## Goal

Publish the verified 1.11.0 development history to GitLab, a filtered public snapshot and release to GitHub, the trimmed official skill store, and leave one English 2.0 preparation issue without altering the active replay task.

## Acceptance Criteria

AC-1 GitLab contains the full v1-11 development commit and no force push is used. AC-2 GitHub main and v1.11.0 release contain only the verified public snapshot with Codex co-author attribution. AC-3 all owner-authored legacy planning issues are closed and one English 2.0 preparation issue remains open. AC-4 the official skill store contains only docs, excel and pdf with valid signatures. AC-5 changelog, release notes and published site state are verified; r111-verification-cycle-replay remains active and unmet. Negative: abort publication instead of overwriting history or publishing private/live state if any snapshot, signature, remote ancestry or secret check is uncertain.

## Plan

## Rollback

Revert the GitLab release commit; remove the GitHub release/tag only if publication validation fails; restore closed owner issues from the recorded list. Never rewrite remote history.

## Journal

- 2026-10-02T16:12:43Z [implementation] — Published development commit 90791fa1 and annotated v1.11.0 tag to GitLab; published verified snapshot e48255c1 and GitHub Release v1.11.0; official store main is 3f73f5e with docs/excel/pdf only and 3/3 Ed25519 verification; closed 96 owner GitHub issues plus GitLab #10 and created GitHub #206 for package-first 2.0.
- 2026-10-02T16:25:16Z [implementation] — Site published from v1.11.0 docs at commit f6b896fe; GitLab pipeline #8726 succeeded and live site returns 1.11.0. Existing KIB-56 Metrika/cookie-consent work was preserved during rebase.
- 2026-10-02T17:49:12Z [implementation] — AC verified: AC-1: ✓ GitLab v1-11 contains development commits through 888d9f70; all pushes were fast-forward and annotated tag v1.11.0 remains 90791fa1. AC-2: ✓ GitHub tag v1.11.0 remains immutable at e48255c1; main is filtered snapshot 4de99f35 with zero leak classes; release is public; workflow run #37038485265 completed success in all four jobs. GitHub resolves metadata commit 3687a408 author to official @codex. AC-3: ✓ legacy owner issues were closed and English GitHub #206 is the sole 2.0 preparation issue. AC-4: ✓ official store main 3f73f5e contains only docs/excel/pdf and signatures verified 3/3. AC-5: ✓ bilingual changelog and release notes are public; site commit f6b896fe pipeline #8726 succeeded and live pages return 200. r111-verification-cycle-replay is still active and unmet. Negative: no force push, no tag move, no private projection in GitHub snapshot.
