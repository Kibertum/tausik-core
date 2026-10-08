---
slug: release-1-10-notes-and-readiness
title: "1.10 release notes describe the rebuilt composition, and every pre-tag check is green"
status: done
epic: release-110-deferred-from-19
story: release110-owner-priorities
complexity: medium
role: docs
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "docs/en/whats-new-1.10.md"
  - "docs/ru/whats-new-1.10.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - "changelog.d/.gitkeep"
  - "tests/test_changelog_fragments.py"
scope_paths:
  - "docs/"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - "changelog.d/"
  - README.md
  - README.ru.md
  - ROADMAP.md
  - "tausik/"
  - "tests/"
scope_tools: []
depends_on: []
completed_at: "2026-09-29T22:55:28Z"
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

Owner, session #279: prepare 1.10 for release. whats-new-1.10 says nothing of the rebuild (README path, tausik demo, answer measure and rules, metrics calls) and misses a behaviour change consumers will hit: since 2d192942 QG-2 applies to every project, so a close without a verify run is refused even where no test gate is configured.

## Acceptance Criteria

AC-1 docs/{en,ru}/whats-new-1.10.md describe the rebuild for the owner's three priorities with the measured numbers. AC-2 The QG-2 change is BREAKING change 6 in both whats-new pages AND marked BREAKING in both changelogs. AC-3 New commands table lists tausik demo and metrics calls. AC-4 changelog assemble --apply folds every fragment; publish senar-check OK; publish snapshot --dry-run shows zero leak classes. AC-5 NEGATIVE: no tag is created and nothing is pushed — those are the owner's acts. AC-6 Full lane and -m slow green.

## Plan

## Rollback

git revert

## Journal

- 2026-09-29T22:55:07Z [implementation] — AC-1: ✓ docs/en/whats-new-1.10.md + docs/ru: 'Rebuilt before release' with the owner's three priorities and numbers (27 undefined terms -> 8/10 cold read; cache 94%, read 31% of calls; answers median 162, p90 365). AC-2: ✓ QG-2-everywhere is breaking change 6 in both whats-new pages; both changelogs mark 6 BREAKING/ЛОМАЮЩЕЕ entries under [Unreleased] (5 existing entries marked, 1 new). AC-3: ✓ New commands table lists tausik demo and tausik metrics calls. AC-4: ✓ changelog assemble --apply folded all fragments (changelog.d keeps a .gitkeep); publish senar-check 'OK: SENAR v1.5 ... is published'; publish snapshot --dry-run: 1587 published, leak classes internal host 0, dev-machine path 0. AC-5 Negative: ✓ no tag created, nothing pushed to either remote. AC-6: ✓ full lane 12592 passed + 2 fixed after (tests/test_changelog_fragments.py, tests/test_prose_language.py green), -m slow 143 passed.
