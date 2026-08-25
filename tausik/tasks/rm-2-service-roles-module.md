---
slug: rm-2-service-roles-module
title: "scripts/service_roles.py — CRUD business logic"
status: done
epic: v13-mcp-and-discipline
story: roles-mcp
complexity: null
role: developer
stack: python
tier: moderate
call_budget: 35
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-26T01:06:28Z"
---

## Goal

New module with role_list, role_show, role_create, role_update, role_delete. Hybrid: writes to roles table + agents/roles/{slug}.md. Delete refuses if role still referenced by tasks.

## Acceptance Criteria

Implemented hybrid roles CRUD: SQLite roles table (migration v18) + markdown profile in agents/roles/<slug>.md; CLI parity in project_cli_role; MCP wrappers in claude+cursor; seed bootstraps from files+task usage. NEGATIVE: delete-with-refs blocked unless force, duplicate slug rejected, unknown slug raises.

## Plan

## Rollback

## Journal

- 2026-04-26T01:06:28Z [implementation] — AC verified: scripts/service_roles.py with role_list/show/create/update/delete + seed_existing_roles ✓ Hybrid: writes table + agents/roles/<slug>.md skeleton ✓ Delete refuses if tasks reference role unless force=True ✓
