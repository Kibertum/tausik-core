---
slug: skill-mcp-parity
title: "MCP skill_list parity + handler path dedup + tool descriptions"
status: done
epic: null
story: null
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "agents/claude/mcp/project/handlers_skill.py, agents/claude/mcp/project/tools_extra.py"
scope_exclude: "scripts/, tests/"
relevant_files:
  - "agents/claude/mcp/project/handlers_skill.py"
  - "agents/claude/mcp/project/tools_extra.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-08T05:15:17Z"
---

## Goal

Fix MCP/CLI integration gaps: skill_list shows AVAILABLE skills in MCP too, deduplicate path-building boilerplate in handlers, fix hardcoded .claude/ in tool descriptions

## Acceptance Criteria

1. MCP tausik_skill_list shows AVAILABLE skills from repos (same as CLI)
2. Path-building boilerplate in handlers_skill.py deduplicated into _skill_paths() helper
3. Tool descriptions use IDE-neutral language (no hardcoded .claude/)
4. No regressions in tests
5. MCP skill_list returns empty result gracefully when no repos configured

## Plan

## Rollback

## Journal

- 2026-04-08T05:12:28Z [implementation] — AC verified: 1. MCP skill_list now shows AVAILABLE from repos ✓ 2. _skill_paths() helper deduplicates 6 handlers ✓ 3. Tool descriptions IDE-neutral ✓ 4. 879 tests pass ✓ 5. Empty repos gracefully handled ✓
