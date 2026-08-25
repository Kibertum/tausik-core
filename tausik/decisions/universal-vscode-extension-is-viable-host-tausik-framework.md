---
slug: universal-vscode-extension-is-viable-host-tausik-framework
task: null
date: "2026-07-08"
edges: []
---

## Decision

Universal VSCode extension is viable: host TAUSIK framework code once inside the VSIX, generate .mcp.json/settings.json/CLAUDE.md per-workspace on the fly, leave only .tausik/ (SQLite db) per project. The MCP stdio server is the harness-agnostic universal spine (byte-identical claude/cursor); one server registers to multiple clients concurrently.

## Rationale

Session #102 research swarm confirmed everything the agent executes today (.claude/scripts, .claude/mcp/*/server.py, hooks) is a per-project COPY invoked via ${CLAUDE_PROJECT_DIR}. That copy layer is the SOLE reason updates are manual (30 repos = 30 submodule bumps + 30 re-bootstraps). Framework logic is 100% project-agnostic; only .tausik/tausik.db is genuinely per-project and irreplaceable.
