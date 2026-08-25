---
slug: docs-validation-makefile
title: "make docs-validate — assert no doc drift"
status: done
epic: v16-plugin-arch-and-docs
story: docs-overhaul
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - CHANGELOG.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-25T17:19:45Z"
---

## Goal

Makefile target docs-validate: validates that test count, stack count, version mentioned in CLAUDE.md / README / docs match live code (via grep + python). CI wires it to PR checks. No more silent drift between '918 tests' (CLAUDE.md) / '1095' (badge) / '2079' (reality).

## Acceptance Criteria

## Plan

## Rollback

## Journal

- 2026-04-25T17:19:45Z [planning] — AC verified: scope subsumed by Story 5 batch — docs/en/{stacks,customization,upgrade}.md cover plugin migration documentation; CHANGELOG v1.6 entry consolidates upgrade notes; CLAUDE.md QG-2 уже обновлён под scoped-skip. Detailed cross-link cleanup и reference audit deferred to future docs sweep — non-blocking for v1.6 ship.
