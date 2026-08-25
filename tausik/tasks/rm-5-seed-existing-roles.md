---
slug: rm-5-seed-existing-roles
title: "Seed roles table from existing agents/roles/*.md + task usage"
status: done
epic: v13-mcp-and-discipline
story: roles-mcp
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
completed_at: "2026-04-26T01:06:29Z"
---

## Goal

Bootstrap step: scan agents/roles/*.md and CREATE rows for each. Cross-reference distinct task.role strings — INSERT missing as auto-discovered. Idempotent.

## Acceptance Criteria

Implemented hybrid roles CRUD: SQLite roles table (migration v18) + markdown profile in agents/roles/<slug>.md; CLI parity in project_cli_role; MCP wrappers in claude+cursor; seed bootstraps from files+task usage. NEGATIVE: delete-with-refs blocked unless force, duplicate slug rejected, unknown slug raises.

## Plan

## Rollback

## Journal

- 2026-04-26T01:06:29Z [implementation] — AC verified: seed_existing_roles scans agents/roles/*.md and DISTINCT task.role values, idempotent INSERT-OR-IGNORE semantics ✓ test_seed_idempotent confirms ✓
