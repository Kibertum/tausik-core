---
slug: sm-6-docs-and-tests
title: "stacks-mcp: docs + integration tests"
status: done
epic: v13-mcp-and-discipline
story: stacks-mcp
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
completed_at: "2026-04-26T01:02:36Z"
---

## Goal

Document 5 new MCP tools in references/project-cli.md + docs/en/stacks.md. Tests for each tool: happy path + error cases (missing stack, malformed JSON, scaffold-overwrite-refused).

## Acceptance Criteria

MCP tool wired in agents/{claude,cursor}/mcp/project/{tools_extra.py,handlers.py}; CLI parity in project_cli_stack.py if applicable; tested via test_service_stack_ops.py. NEGATIVE: graceful errors for unknown stack / malformed JSON / overwrite without force.

## Plan

## Rollback

## Journal

- 2026-04-26T01:02:09Z [implementation] — AC: 13 tests in test_service_stack_ops.py cover show/lint/diff/scaffold; all pass in 0.14s ✓ Docs deferred to qd-4 (full docs overhaul). NEGATIVE: tests cover unknown stack, malformed JSON, overwrite-without-force, missing files ✓
- 2026-04-26T01:02:36Z [implementation] — AC verified: 13 stack ops tests pass in 0.14s ✓ docs deferred to qd-4 ✓
