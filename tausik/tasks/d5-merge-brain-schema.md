---
slug: d5-merge-brain-schema
title: "Brain schema merge"
status: done
epic: docs-overhaul-v13
story: references-merge
complexity: null
role: tech-writer
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
completed_at: "2026-04-26T15:40:30Z"
---

## Goal

Move references/brain-db-schema.md to docs/en/brain-db-schema.md + create RU translation

## Acceptance Criteria

1. references/brain-db-schema.md copied to docs/en/brain-db-schema.md with bilingual switcher header. 2. docs/ru/brain-db-schema.md created (concise concept overview pointing to EN for full spec). 3. Both link to shared-brain.md and architecture.md. NEGATIVE: original references file marked for delete in d5-cleanup.

## Plan

## Rollback

## Journal

- 2026-04-26T15:40:30Z [implementation] — AC verified: docs/en/brain-db-schema.md exists with bilingual header ✓ docs/ru/brain-db-schema.md created with 4-DB overview + privacy + pull-sync + scrubbing sections ✓ both cross-link to shared-brain.md and architecture.md ✓ NEGATIVE: references/brain-db-schema.md marked for d5-cleanup deletion
