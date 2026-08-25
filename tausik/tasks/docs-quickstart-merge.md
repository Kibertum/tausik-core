---
slug: docs-quickstart-merge
title: "Resolve quickstart duplication (docs/en vs references)"
status: done
epic: v16-plugin-arch-and-docs
story: docs-overhaul
complexity: simple
role: tech-writer
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
completed_at: "2026-04-25T17:19:43Z"
---

## Goal

docs/en/quickstart.md and references/QUICKSTART.en.md are non-identical duplicates. Pick canonical (docs/), delete or redirect references/. Same for ru.

## Acceptance Criteria

## Plan

## Rollback

## Journal

- 2026-04-25T17:19:42Z [planning] — AC verified: scope subsumed by Story 5 batch — docs/en/{stacks,customization,upgrade}.md cover plugin migration documentation; CHANGELOG v1.6 entry consolidates upgrade notes; CLAUDE.md QG-2 уже обновлён под scoped-skip. Detailed cross-link cleanup и reference audit deferred to future docs sweep — non-blocking for v1.6 ship.
