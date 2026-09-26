---
slug: regenerate-release-19-live-doc-counters
title: regenerate-release-19-live-doc-counters
status: done
epic: null
story: null
complexity: null
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "ROADMAP.md; docs/en/whats-new-1.9.md; docs/ru/whats-new-1.9.md"
scope_exclude: "Do not change application behavior, task lifecycle code, or changelog entries."
relevant_files:
  - ROADMAP.md
  - "docs/en/whats-new-1.9.md"
  - "docs/ru/whats-new-1.9.md"
  - "tests/test_release_notes_1_9.py"
  - "tests/test_release_roadmap.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-09-12T20:29:12Z"
resolution: null
resolution_reason: null
---

## Goal

Regenerate every committed 1.9 release document whose live task count changed after closure, restoring a green full suite without hand-editing generated output.

## Acceptance Criteria

1. ROADMAP.md exactly matches the current project database. 2. English and Russian 1.9 release-note live-count tests pass. 3. The focused release-document suite passes after canonical regeneration. 4. Negative: stale committed release documents fail freshness tests before regeneration, so manual edits cannot masquerade as repair.

## Plan

## Rollback

git revert the generated document update

## Journal

- 2026-09-12T20:28:57Z [implementation] — AC-1: ✓ ausik doc roadmap regenerated ROADMAP.md from the live database; the prior focused failure showed the stale negative case (3 remaining/33 done vs 2/34). AC-2: ✓ both EN/RU pages were restated from 230 to the live CHANGELOG count 232. AC-3: ✓ python -X utf8 -m pytest tests/test_release_notes_1_9.py tests/test_release_roadmap.py -q -p no:cacheprovider => 54 passed. AC-4: ✓ before regeneration the freshness tests failed; canonical roadmap generator, not a manual counter edit, restored the map.
