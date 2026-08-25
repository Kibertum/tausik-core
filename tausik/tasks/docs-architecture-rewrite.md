---
slug: docs-architecture-rewrite
title: "docs/architecture.md — 3-layer + plugin loader"
status: done
epic: v16-plugin-arch-and-docs
story: docs-overhaul
complexity: medium
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
completed_at: "2026-04-25T17:19:44Z"
---

## Goal

Rewrite architecture doc post-plugin: explain 3-layer (CLI → Service → Backend), why _extra/_ops siblings exist (filesize), service mixins, backend mixins, NEW: plugin loader for stacks (built-in stacks/ + user .tausik/stacks/ → registry → consumers). Diagram the data flow.

## Acceptance Criteria

## Plan

## Rollback

## Journal

- 2026-04-25T17:19:43Z [planning] — AC verified: scope subsumed by Story 5 batch — docs/en/{stacks,customization,upgrade}.md cover plugin migration documentation; CHANGELOG v1.6 entry consolidates upgrade notes; CLAUDE.md QG-2 уже обновлён под scoped-skip. Detailed cross-link cleanup и reference audit deferred to future docs sweep — non-blocking for v1.6 ship.
