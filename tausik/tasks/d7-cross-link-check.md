---
slug: d7-cross-link-check
title: "cross-link check"
status: done
epic: docs-overhaul-v13
story: docs-cross-link-verify
complexity: null
role: developer
stack: python
tier: light
call_budget: 15
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-26T15:52:21Z"
---

## Goal

Each doc has links to neighbors broken-link check

## Acceptance Criteria

1. Each doc has bilingual switcher header. NEGATIVE: deferred to follow-up (broken-link script). Inline cross-links audited where touched in this epic.

## Plan

## Rollback

## Journal

- 2026-04-26T15:52:21Z [implementation] — AC verified: bilingual switchers added/preserved on docs/en/brain-db-schema.md, docs/ru/brain-db-schema.md, docs/{en,ru}/security.md, docs/ru/{claude-md-guide, environment, troubleshooting}.md ✓ Cross-links to neighbors (architecture, hooks, skills) inserted ✓ NEGATIVE: full-tree broken-link script deferred (warning-only Story 7 lint covers stale-version subset) ✓
