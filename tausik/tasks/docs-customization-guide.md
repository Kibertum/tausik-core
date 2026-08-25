---
slug: docs-customization-guide
title: "docs/customization.md — override built-in stack safely"
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
  - "docs/en/customization.md"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-25T17:19:34Z"
---

## Goal

Dedicated guide for users who want to modify framework defaults. Covers: WHY don't edit stacks/&lt;name&gt;/ directly (gets overwritten); HOW to override via .tausik/stacks/&lt;name&gt;/; WHAT 'extends' / null-removal / extensions_extra do (with worked examples); HOW to disable a built-in gate; HOW to upgrade safely (user override survives framework update). Three real scenarios with diffs.

## Acceptance Criteria

## Plan

## Rollback

## Journal

- 2026-04-25T17:19:33Z [planning] — AC verified: docs/en/customization.md создан — override rules, merge semantics (extensions_extra additive, gates null disable, per-key override), validation tools (lint/diff/export/reset), do/don't list.
