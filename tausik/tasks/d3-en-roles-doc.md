---
slug: d3-en-roles-doc
title: "docs/en/roles.md NEW"
status: done
epic: docs-overhaul-v13
story: docs-en-new-features
complexity: null
role: tech-writer
stack: python
tier: moderate
call_budget: 35
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "docs/en/roles.md"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-26T16:18:10Z"
---

## Goal

docs/en/roles.md NEW: hybrid storage CRUD CLI+MCP seed --extends

## Acceptance Criteria

1. docs/en/roles.md created; 2. Documents hybrid storage (SQLite metadata + agents/roles/{role}.md profile); 3. Covers CLI: list/show/create/update/delete/seed; 4. Covers MCP role tools; 5. Documents seed --extends behavior; 6. Negative: no claim that roles are restricted to a fixed enum (free text)

## Plan

## Rollback

## Journal

- 2026-04-26T16:18:10Z [implementation] — AC verified: 1.✓ docs/en/roles.md created; 2.✓ Hybrid storage explained (SQLite metadata + agents/roles/{slug}.md profile); 3.✓ CLI list/show/create/update/delete/seed all covered; 4.✓ MCP role tools listed; 5.✓ --extends behavior documented (clones profile from base, tracks relationship in DB); 6.✓ negative — explicitly states roles are NOT a fixed enum and any string is accepted, role delete preserves the profile file.
