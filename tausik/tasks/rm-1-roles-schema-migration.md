---
slug: rm-1-roles-schema-migration
title: "Schema: add `roles` table + migration"
status: done
epic: v13-mcp-and-discipline
story: roles-mcp
complexity: null
role: developer
stack: python
tier: light
call_budget: 25
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-26T01:06:27Z"
---

## Goal

New SQLite table `roles` (slug PK, title, description, created_at, updated_at). Migration in backend_migrations.py preserves existing free-text role values from tasks (auto-create rows for distinct strings).

## Acceptance Criteria

Implemented hybrid roles CRUD: SQLite roles table (migration v18) + markdown profile in agents/roles/<slug>.md; CLI parity in project_cli_role; MCP wrappers in claude+cursor; seed bootstraps from files+task usage. NEGATIVE: delete-with-refs blocked unless force, duplicate slug rejected, unknown slug raises.

## Plan

## Rollback

## Journal

- 2026-04-26T01:06:27Z [implementation] — AC verified: migration v18 adds roles table (slug PK + title/description/created_at/updated_at) ✓ SCHEMA_VERSION bumped to 18 ✓
