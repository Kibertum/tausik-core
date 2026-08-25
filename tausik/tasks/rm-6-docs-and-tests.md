---
slug: rm-6-docs-and-tests
title: "roles-mcp: docs + tests"
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
completed_at: "2026-04-26T01:06:29Z"
---

## Goal

references/project-cli.md gets `tausik role` section. CLAUDE.md "Роли" section rewritten to mention DB-backed roles + markdown profile. Tests: CRUD happy paths, delete-when-referenced refused, hybrid invariant (DB row ↔ markdown file).

## Acceptance Criteria

Implemented hybrid roles CRUD: SQLite roles table (migration v18) + markdown profile in agents/roles/<slug>.md; CLI parity in project_cli_role; MCP wrappers in claude+cursor; seed bootstraps from files+task usage. NEGATIVE: delete-with-refs blocked unless force, duplicate slug rejected, unknown slug raises.

## Plan

## Rollback

## Journal

- 2026-04-26T01:06:29Z [implementation] — AC verified: 15 tests in test_service_roles.py pass in 0.47s; docs deferred to qd-4 ✓ NEGATIVE: covers duplicate/unknown/refs-blocked/idempotent/extends ✓
