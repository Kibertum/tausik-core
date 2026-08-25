---
slug: sm-5-stack-scaffold-mcp
title: "MCP: tausik_stack_scaffold — generate skeleton stack.json"
status: done
epic: v13-mcp-and-discipline
story: stacks-mcp
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
completed_at: "2026-04-26T01:02:36Z"
---

## Goal

MCP tool that creates .tausik/stacks/{name}/stack.json with skeleton (name, version, empty detect/extensions/gates) + skeleton guide.md. If extends_builtin given, generates `extends: "builtin:NAME"` shape. Refuses overwrite without explicit force.

## Acceptance Criteria

MCP tool wired in agents/{claude,cursor}/mcp/project/{tools_extra.py,handlers.py}; CLI parity in project_cli_stack.py if applicable; tested via test_service_stack_ops.py. NEGATIVE: graceful errors for unknown stack / malformed JSON / overwrite without force.

## Plan

## Rollback

## Journal

- 2026-04-26T01:02:08Z [implementation] — AC: tausik_stack_scaffold + tausik stack scaffold CLI create skeleton stack.json + guide.md; --extends sets builtin:X reference ✓ NEGATIVE: refuses overwrite without force (FileExistsError → 'Refused: ...') ✓
- 2026-04-26T01:02:36Z [implementation] — AC verified: tausik_stack_scaffold MCP + CLI create stack.json + guide.md skeleton; --extends sets builtin:X ✓ refuses overwrite without force ✓
