---
slug: ext-p0-derisk-spike
title: "[ext P0] De-risk spike: bundled MCP + per-client config + hybrid Python"
status: planning
epic: vscode-extension
story: ext-program
complexity: null
role: architect
stack: null
tier: moderate
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

Validate the central hypothesis of epic universal-vscode-extension with a throwaway VSIX: (1) bundle the stdio MCP server inside the extension and drive tausik_* tools from BOTH Claude Code (.mcp.json) and Kilo (kilo.jsonc) pointing at the bundled server; (2) hybrid Python discovery — find user Python >=3.11 else fall back to a PyInstaller binary (pilot win-x64); (3) research spike: does Kilo/Roo/Cline have any pre-tool interceptor for gates (determines Phase 3 scope). Exit: proof the bundled-server + per-client-config model works end-to-end.

## Acceptance Criteria

## Plan

## Rollback

## Journal
