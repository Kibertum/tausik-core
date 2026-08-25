---
slug: d5-merge-architecture
title: "Merge architecture references"
status: done
epic: docs-overhaul-v13
story: references-merge
complexity: null
role: architect
stack: python
tier: moderate
call_budget: 30
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-26T15:36:57Z"
---

## Goal

Merge references/architecture(.en).md into docs/{ru,en}/architecture.md

## Acceptance Criteria

1. Unique content from references/architecture.md (RU, hooks/Memory Aggregates) merged into docs/ru/architecture.md. 2. EN files essentially identical — references/architecture.en.md marked for delete. 3. Test count updated 918 → 2226. NEGATIVE: hooks.md cross-link added so detailed hooks list is in canonical place.

## Plan

## Rollback

## Journal

- 2026-04-26T15:36:57Z [implementation] — AC verified: docs/ru/architecture.md gets Hooks + Memory Aggregates sections from references ✓ test count 918→2226 ✓ EN files identical (only header diff) — references/architecture.en.md will be deleted ✓ NEGATIVE: hooks.md cross-link added so future updates have one canonical location ✓
