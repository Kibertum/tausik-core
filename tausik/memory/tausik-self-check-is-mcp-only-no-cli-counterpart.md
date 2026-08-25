---
slug: tausik-self-check-is-mcp-only-no-cli-counterpart
title: "tausik_self_check is MCP-only — no CLI counterpart"
type: gotcha
tags:
  - cli
  - discoverability
  - mcp
  - self_check
task: null
edges: []
---

`.tausik/tausik self-check` errors with `invalid choice: 'self-check'`. The drift / sibling-MCP detection lives only in the MCP tool `tausik_self_check`. /start skill calls the MCP tool directly. If MCP is unavailable (server hung), there is no CLI fallback for the diagnosis itself — only the workaround (use CLI for verify/task done) is documented.

Don't guess CLI subcommands — read references/project-cli.md or tausik &lt;cmd&gt; --help. Burned ~30s and a tool call this session by guessing.

If a CLI counterpart is desired in future, would map to project_cli_doctor (since `tausik doctor` already runs health checks).
