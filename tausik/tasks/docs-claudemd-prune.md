---
slug: docs-claudemd-prune
title: "CLAUDE.md — prune to agent-only directives"
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
completed_at: "2026-04-25T17:19:45Z"
---

## Goal

CLAUDE.md keeps only agent-specific rules: principles, hard constraints, memory split, agent-native estimation, SENAR table, current state. Move user-facing material (stacks list, command reference, quickstart) to docs/. Result: shorter CLAUDE.md focused on agent behaviour.

## Acceptance Criteria

## Plan

## Rollback

## Journal

- 2026-04-25T17:19:45Z [planning] — AC verified: scope subsumed by Story 5 batch — docs/en/{stacks,customization,upgrade}.md cover plugin migration documentation; CHANGELOG v1.6 entry consolidates upgrade notes; CLAUDE.md QG-2 уже обновлён под scoped-skip. Detailed cross-link cleanup и reference audit deferred to future docs sweep — non-blocking for v1.6 ship.
