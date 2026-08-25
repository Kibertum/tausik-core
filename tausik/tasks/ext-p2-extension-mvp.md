---
slug: ext-p2-extension-mvp
title: "[ext P2] Extension MVP: activation, .tausik provisioning, MCP registration, skills"
status: planning
epic: vscode-extension
story: ext-program
complexity: null
role: developer
stack: null
tier: deep
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

Build the extension itself. Activation event; .tausik/ (db+config) provisioning per workspace via workspace.fs (multi-root aware); MCP registration = contributes.mcpServerDefinitionProviders (VS Code native) + writers for .mcp.json (Claude Code) and kilo.jsonc (Kilo); skills into .claude/skills (shared Claude+Kilo); session_start + skill-rebuild on activation (replaces the SessionStart hook for non-Claude). Publish to BOTH MS Marketplace AND Open VSX (Cursor needs Open VSX; auto-update requires marketplace, not VSIX sideload).

## Acceptance Criteria

## Plan

## Rollback

## Journal
