---
slug: rm-3-cli-parity
title: "CLI: tausik role {list,show,create,update,delete}"
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

argparse subparsers in project_parser.py + dispatchers in project_cli_ops.py for full CRUD CLI parity with MCP. `role show` includes markdown profile content. `role create --extends developer` clones existing.

## Acceptance Criteria

Implemented hybrid roles CRUD: SQLite roles table (migration v18) + markdown profile in agents/roles/<slug>.md; CLI parity in project_cli_role; MCP wrappers in claude+cursor; seed bootstraps from files+task usage. NEGATIVE: delete-with-refs blocked unless force, duplicate slug rejected, unknown slug raises.

## Plan

## Rollback

## Journal

- 2026-04-26T01:06:28Z [implementation] — AC verified: tausik role {list,show,create,update,delete,seed} via project_cli_role + project_parser_role ✓ create --extends clones profile from parent ✓ wired in project.py dispatch ✓
