---
slug: frai-to-tausik-official-skills
title: "Rebrand frai→tausik in jira/bitrix24 official skills"
status: done
epic: null
story: null
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "skills-official/jira/mcp/server.py"
  - "skills-official/jira/mcp/handlers.py"
  - "skills-official/jira/mcp/tools.py"
  - "skills-official/bitrix24/mcp/server.py"
  - "skills-official/bitrix24/mcp/handlers.py"
  - "skills-official/bitrix24/mcp/tools.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-07T20:10:09Z"
---

## Goal

Replace all frai references with tausik in skills-official/jira and skills-official/bitrix24 MCP code — function names, paths, comments, DB references

## Acceptance Criteria

1. Zero occurrences of "frai" in skills-official/**/*.py
2. Function names, DB paths, table columns renamed frai→tausik
3. pytest passes
4. bootstrap.py runs without errors

## Plan

## Rollback

## Journal

- 2026-04-07T20:02:09Z [implementation] — AC verified: 1) grep -rl frai skills-official/ = 0 results 2) _frai_db→_tausik_db, frai_slug→tausik_slug, .frai/frai.db→.tausik/tausik.db in all 6 files 3) pytest: 837 passed 4) bootstrap: success, 0 frai in .claude/
