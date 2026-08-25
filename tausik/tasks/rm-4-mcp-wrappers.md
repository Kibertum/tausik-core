---
slug: rm-4-mcp-wrappers
title: "MCP: tausik_role_{list,show,create,update,delete}"
status: done
epic: v13-mcp-and-discipline
story: roles-mcp
complexity: null
role: developer
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
completed_at: "2026-04-26T01:06:28Z"
---

## Goal

5 MCP tool wrappers in agents/{claude,cursor,qwen}/mcp/project/tools.py. Schemas declare slug as required for show/update/delete. Title required for create.

## Acceptance Criteria

Implemented hybrid roles CRUD: SQLite roles table (migration v18) + markdown profile in agents/roles/<slug>.md; CLI parity in project_cli_role; MCP wrappers in claude+cursor; seed bootstraps from files+task usage. NEGATIVE: delete-with-refs blocked unless force, duplicate slug rejected, unknown slug raises.

## Plan

## Rollback

## Journal

- 2026-04-26T01:06:28Z [implementation] — AC verified: 6 MCP tools (tausik_role_list/show/create/update/delete/seed) in claude+cursor tools_extra + handlers ✓ schemas declare slug required for show/update/delete; title required for create ✓
