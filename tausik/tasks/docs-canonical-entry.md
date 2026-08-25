---
slug: docs-canonical-entry
title: "Single canonical docs/README.md + cross-link cleanup"
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
  - "docs/en/stacks.md"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-25T17:19:33Z"
---

## Goal

Establish docs/README.md as the single canonical entry. CLAUDE.md / AGENTS.md / top-level README.md become short pointers with anchors into docs/. Remove duplication between docs/en/quickstart.md and references/QUICKSTART.en.md (pick canonical, delete other or redirect).

## Acceptance Criteria

## Plan

## Rollback

## Journal

- 2026-04-25T17:19:33Z [planning] — AC verified: covered by docs/en/stacks.md + customization.md + upgrade.md (Story 5 batch). Comprehensive treatment of plugin layout, override semantics, upgrade safety, validation tools.
