---
slug: roadmap-stale-after-second-model-review
title: "Синхронизировать ROADMAP с live DB после review"
status: active
epic: release-19-renar-conformance
story: release19-proof-integrity
complexity: simple
role: tech-writer
stack: python
tier: null
call_budget: null
defect_of: codex-second-model-review-of-sessions-243-250
scope: null
scope_exclude: null
relevant_files:
  - ROADMAP.md
  - "tests/test_release_roadmap.py"
scope_paths:
  - ROADMAP.md
  - "tausik/tasks/roadmap-stale-after-second-model-review.md"
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

Regenerate the committed ROADMAP.md from the live TAUSIK database so the release roadmap ratchet reflects current task counters.

## Acceptance Criteria

AC-1: tausik doc roadmap produces a committed map equal to the live database. AC-2: tests/test_release_roadmap.py::TestCommittedMapIsCurrent::test_the_committed_map_is_not_stale passes. AC-3 (negative): a deliberately stale map is still rejected. AC-4: scoped verify passes.

## Plan

## Rollback

Revert the generated ROADMAP.md update.

## Journal

- 2026-09-12T19:54:07Z [implementation] — AC verified: 1. ✓ tausik doc roadmap regenerated ROADMAP.md from the live database; 2. ✓ tests/test_release_roadmap.py::TestCommittedMapIsCurrent::test_the_committed_map_is_not_stale passed; 3. ✓ the pre-regeneration full lane reproduced the stale-map failure; 4. running signed verify now.
