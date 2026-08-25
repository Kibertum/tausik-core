---
slug: honest-ide-support-table-in-readme
title: "Honest IDE support table in README"
status: done
epic: null
story: null
complexity: simple
role: tech-writer
stack: null
tier: null
call_budget: null
defect_of: null
scope: "README.md, README.ru.md"
scope_exclude: null
relevant_files:
  - README.md
  - README.ru.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-07T13:43:54Z"
---

## Goal

IDE support table honestly reflects what each IDE gets — hooks are Claude Code only, other IDEs get MCP+Rules without enforcement hooks

## Acceptance Criteria

1. IDE table in README.md/README.ru.md shows what each IDE actually gets (MCP, Skills, Hooks, Rules). 2. Claude Code shows hooks as unique feature. 3. Cursor/Windsurf show MCP+Rules but no hooks. 4. No IDE falsely claims "Full support" if hooks are missing. 5. Negative: Cursor user reading the table won't feel misled about what they get.

## Plan

## Rollback

## Journal

- 2026-04-07T13:43:48Z [implementation] — AC verified: 1. IDE table now has 4 columns (MCP/Skills/Hooks/Rules) showing exact capabilities ✓ 2. Claude Code shows all 4 hooks ✓ 3. Cursor/Windsurf show "—" for hooks ✓ 4. No "Full support" claim for IDEs without hooks ✓ 5. Explanatory paragraph clarifies what hooks do and that QG still works without them ✓
