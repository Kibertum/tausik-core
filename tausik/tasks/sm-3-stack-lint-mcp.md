---
slug: sm-3-stack-lint-mcp
title: "MCP: tausik_stack_lint — validate user override against schema"
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
completed_at: "2026-04-26T01:02:36Z"
---

## Goal

MCP tool that runs validate_decl() against user override .tausik/stacks/{name}/stack.json. Returns list of error strings or empty if valid.

## Acceptance Criteria

MCP tool wired in agents/{claude,cursor}/mcp/project/{tools_extra.py,handlers.py}; CLI parity in project_cli_stack.py if applicable; tested via test_service_stack_ops.py. NEGATIVE: graceful errors for unknown stack / malformed JSON / overwrite without force.

## Plan

## Rollback

## Journal

- 2026-04-26T01:02:08Z [implementation] — AC: tausik_stack_lint validates every .tausik/stacks/<name>/stack.json via validate_decl, returns {checked,failed,results} ✓ NEGATIVE: malformed JSON → marks failed, doesn't crash; missing dir → empty result ✓
- 2026-04-26T01:02:36Z [implementation] — AC verified: tausik_stack_lint walks .tausik/stacks/, validates each via validate_decl ✓ malformed JSON marked failed ✓
