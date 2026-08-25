---
slug: sm-1-stack-list-mcp
title: "MCP: tausik_stack_list — all registered stacks with source"
status: done
epic: v13-mcp-and-discipline
story: stacks-mcp
complexity: null
role: developer
stack: python
tier: trivial
call_budget: 10
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

MCP tool returning list of {name, source: builtin|user|overridden, guide_path}. Wraps `StackRegistry.all_stacks()` + `source_for()`.

## Acceptance Criteria

MCP tool wired in agents/{claude,cursor}/mcp/project/{tools_extra.py,handlers.py}; CLI parity in project_cli_stack.py if applicable; tested via test_service_stack_ops.py. NEGATIVE: graceful errors for unknown stack / malformed JSON / overwrite without force.

## Plan

## Rollback

## Journal

- 2026-04-26T01:02:08Z [implementation] — AC: tausik_stack_list MCP tool added to claude+cursor tools_extra.py + handler delegates to svc.stack_list() ✓ NEGATIVE: empty registry → empty list ✓
- 2026-04-26T01:02:35Z [implementation] — AC verified: tausik_stack_list MCP wired in claude+cursor tools_extra ✓ delegates to svc.stack_list ✓
