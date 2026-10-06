---
slug: publish-tausik-1-11-2-to-the-github-release-mirror
title: "Publish TAUSIK 1.11.2 to the GitHub release mirror"
status: done
epic: null
story: null
complexity: null
role: developer
stack: null
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "docs/en/whats-new-1.11.md"
  - "docs/ru/whats-new-1.11.md"
  - release-body-1.11.2.md
  - "tausik/published_tags.json"
scope_paths: []
scope_tools: []
assurance_profiles: []
assurance_impact: null
depends_on: []
completed_at: "2026-10-06T21:28:49Z"
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

Complete the decision-368 publication ritual for 1.11.2: bump the whats-new Release links to v1.11.2, add the release body, cut the final release notes pass, rebuild and verify the filtered snapshot on the public head, push main and the refspec tag to GitHub, run the SENAR edition check, and record the published tag.

## Acceptance Criteria

1) publish notes --version 1.11.2 accepts release-body-1.11.2.md (both whats-new pages linked). 2) publish verify proves the snapshot tree equals the filtered tree of v1.11.2. 3) Negative: senar-check exits 0 while the claimed SENAR edition tag is missing on GitHub, the release stays untagged there. 4) github main and tags/v1.11.2 point at the verified snapshot; published_tags.json records v1.11.2 with the snapshot sha.

## Plan

## Rollback

## Journal

- 2026-10-06T21:28:38Z [implementation] — AC verified: 1) ✓ publish notes --version 1.11.2 accepted release-body-1.11.2.md, both whats-new pages linked — commit 43083102 (docs/en/whats-new-1.11.md, docs/ru/whats-new-1.11.md, release-body-1.11.2.md). 2) ✓ publish verify proved snapshot tree == filtered tree of v1.11.2 — verify runs #3543/#3544 PASS in session #293. 3) ✓ Negative: senar-check exit-0-with-missing-edition-tag leaves the GitHub release untagged — exercised on the 1.11.2 pass in session #293 before tagging. 4) ✓ live ls-remote github: refs/heads/main = refs/tags/v1.11.2 = 68b43c4632fcb778f5bd559ca3b223d89e42d570; published_tags.json records v1.11.2 -> 68b43c46 (commit 44313253, pushed origin v1-11-2 43083102..44313253, main untouched per 1.11.1 precedent); tests/test_published_tags_are_promises.py 9 passed. Closure: --no-changelog — publication mechanics are recorded in whats-new Release links + release body + published_tags.json; an [Unreleased] CHANGELOG line would duplicate the [1.11.2] section.
