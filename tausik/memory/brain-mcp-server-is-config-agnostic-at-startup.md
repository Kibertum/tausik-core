---
slug: brain-mcp-server-is-config-agnostic-at-startup
title: "Brain MCP server is config-agnostic at startup"
type: convention
tags:
  - architecture
  - bootstrap
  - brain
  - mcp
task: brain-mcp-server-wiring
edges: []
---

agents/claude/mcp/brain/server.py does NOT read brain_config at startup. The server always registers + lists tools; handlers return a "not configured" setup hint only when a tool is called on a disabled brain. This decouples init-wizard from bootstrap: flipping brain.enabled does not require re-running bootstrap to activate the MCP endpoint. Contrast with the historical pattern where MCP entries gate on config — avoid that; idempotent registration is cleaner.
