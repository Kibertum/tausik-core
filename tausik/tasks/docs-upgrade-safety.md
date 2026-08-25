---
slug: docs-upgrade-safety
title: "docs/upgrade.md — what happens to user data on framework upgrade"
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
  - "docs/en/upgrade.md"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-25T17:19:34Z"
---

## Goal

docs/upgrade.md: which files bootstrap regenerates (.claude/, .cursor/, stacks/), which it NEVER touches (.tausik/stacks/, .tausik/config.json, .tausik/tausik.db). Migration story for older config formats. Edge cases: user override references built-in field that framework renamed.

## Acceptance Criteria

## Plan

## Rollback

## Journal

- 2026-04-25T17:19:34Z [planning] — AC verified: docs/en/upgrade.md создан — bootstrap-owned vs user-owned tree, .tausik/ contract (NEVER touched), upgrade workflow, breakage scenarios, disaster recovery.
