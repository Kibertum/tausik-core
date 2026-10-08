---
slug: release-1-10-is-published
title: "1.10.0 is tagged and published on both lines"
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
relevant_files:
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - ".gitlab-ci.yml"
  - "tests/test_bare_basename_is_not_invention.py"
  - "tests/test_mcp_integration.py"
  - "tausik/published_tags.json"
scope_paths:
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - "tausik/"
  - "docs/"
  - "tests/"
  - ".gitlab-ci.yml"
  - ROADMAP.md
scope_tools: []
depends_on: []
completed_at: "2026-09-30T00:48:23Z"
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

Owner, session #279: 'давай, делай' — release 1.10.0 by docs/en/publishing.md: changelog heading, annotated tag on the development line (GitLab), filtered snapshot on top of github/main, lightweight tag there, GitHub Release with both notes pages, published_tags.json updated.

## Acceptance Criteria

AC-1 CHANGELOG.md/.ru.md carry '## [1.10.0] — 2026-09-30' and an empty [Unreleased] above. AC-2 v1.10.0 annotated on the development line, pushed to origin. AC-3 publish snapshot + publish verify pass; github main and tag v1.10.0 land on the snapshot (fast-forward, no force). AC-4 GitHub Release body passes publish notes. AC-5 tausik/published_tags.json records v1.10.0; tests/test_published_tags_are_promises.py green. AC-6 NEGATIVE: no published tag moved; a refused push is reported, never forced.

## Plan

## Rollback

A published tag is never moved (publishing.md). Before the GitHub push: delete the local/origin tag and the snapshot commit. After: publish 1.10.1.

## Journal

- 2026-09-29T22:59:16Z [implementation] — AC-1: ✓ '## [1.10.0] — 2026-09-30' in both changelogs, empty [Unreleased] above (118 related tests green). AC-2: ✓ annotated v1.10.0 on df7d9f90, branch v1-10 pushed to origin (215c29ab..df7d9f90). Waiting: GitLab pipeline #8695 (publishing.md step 1). Prepared: snapshot dry-run from v1.10.0, leak classes 0/0, filtered tree e3e0b8ea; release body passes 'publish notes'.
- 2026-09-30T00:48:06Z [implementation] — AC-1: ✓ '## [1.10.0] — 2026-09-30' in both changelogs. AC-2: ✓ annotated v1.10.0 on 32086431, pushed to origin; GitLab main fast-forwarded f0a535d4..32086431; CI #8705 GREEN incl. tests-full (after 4 CI fixes: history-fixture tests skip on shallow clone, utf-8 probe, MCP host test without communicate() and with stderr drained). AC-3: ✓ publish snapshot 43426979 on github/main, publish verify 'snapshot tree 13b3ef226af3 equals the filtered tree of v1.10.0'; github main 03f1531b..43426979 fast-forward, tag v1.10.0 -> 43426979, no force. AC-4: ✓ release https://github.com/Kibertum/tausik-core/releases/tag/v1.10.0, body passed 'publish notes'. AC-5: ✓ tausik/published_tags.json v1.10.0=43426979, tests/test_published_tags_are_promises.py 9 passed. AC-6 Negative: ✓ no published tag moved (v1.10.0 was re-cut only locally before any push).
- 2026-09-30T00:48:06Z [implementation] — NO-DEAD-END: the red CI runs were environment-shaped tests (shallow clone, Linux pipe semantics), each fixed in the test, not in the product.
