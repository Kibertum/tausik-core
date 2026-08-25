---
slug: d7-stale-version-lint
title: "stale-version lint"
status: done
epic: docs-overhaul-v13
story: docs-cross-link-verify
complexity: null
role: developer
stack: python
tier: light
call_budget: 20
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/docs_lint.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-26T15:52:20Z"
---

## Goal

Lint script: WARN (not block) when v1.2 / 82 tools / 1095 tests / frai mentioned in any doc except CHANGELOG history. Exit 0 always — informational only.

## Acceptance Criteria

1. scripts/docs_lint.py exists. 2. Warning-only (exit 0 always). 3. Detects v1.0/v1.1/v1.2 + tool/skill/test counts + frai legacy name. NEGATIVE: CHANGELOG excluded; works on Win cp1252 console (utf-8 reconfigure).

## Plan

## Rollback

## Journal

- 2026-04-26T15:52:20Z [implementation] — AC verified: scripts/docs_lint.py created (10 patterns: stale-version, 82/80 tools, 75/73 project, 918/1095 tests, 34 skills, 13 hooks, frai legacy) ✓ exit 0 always — warning-only ✓ Windows cp1252 fix via reconfigure utf-8 errors=replace ✓ NEGATIVE: CHANGELOG.md in _EXCLUDE set ✓ Initial scan reduced 49→28 stale mentions after fixes ✓
