---
slug: sm-2-stack-show-mcp
title: "MCP: tausik_stack_show — resolved decl + source tracking"
status: done
epic: v13-mcp-and-discipline
story: stacks-mcp
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
completed_at: "2026-04-26T01:02:35Z"
---

## Goal

MCP tool returning resolved stack decl (after merge of builtin + user override) with source breakdown per field. Includes guide content if requested.

## Acceptance Criteria

MCP tool wired in agents/{claude,cursor}/mcp/project/{tools_extra.py,handlers.py}; CLI parity in project_cli_stack.py if applicable; tested via test_service_stack_ops.py. NEGATIVE: graceful errors for unknown stack / malformed JSON / overwrite without force.

## Plan

## Rollback

## Journal

- 2026-04-26T01:02:08Z [implementation] — AC: tausik_stack_show wraps service_stack_ops.stack_show, returns resolved decl with source/is_user_overridden ✓ NEGATIVE: unknown stack raises KeyError → handler returns 'Error: ...' ✓
- 2026-04-26T01:02:35Z [implementation] — AC verified: tausik_stack_show wraps service_stack_ops.stack_show ✓ unknown stack returns Error ✓
