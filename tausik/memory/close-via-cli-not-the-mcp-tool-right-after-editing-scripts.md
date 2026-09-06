---
slug: close-via-cli-not-the-mcp-tool-right-after-editing-scripts
title: "Close via CLI, not the MCP tool, right after editing scripts/harness in the same session"
type: gotcha
tags: []
task: null
edges: []
---

The tausik-project MCP server is a long-running process that does NOT hot-reload scripts/harness edits made mid-session. Calling tausik_verify/tausik_task_done via MCP right after editing scripts/*.py or harness/claude/mcp/project/*.py in the same session hits bootstrap_drift ("Stale process: N file(s)...changed AFTER it started") and claudemd_state_drift ("Database schema vN is newer than code vN-1") — the MCP process is executing an import snapshot from before your edits, even after `python bootstrap/bootstrap.py --ide all`. Separately, the MCP tausik_verify call can also spuriously report a scoped pytest FAIL that never actually failed — the same scoped run passed cleanly when re-run via `.tausik/tausik verify --task <slug>` directly (CLI), taking ~95s; the MCP tool call likely has a shorter internal timeout than a large scoped pytest run needs, and truncates/kills it, misreporting FAIL. Fix: after any scripts/ or harness/ edit, run `tausik verify --task <slug>` and `tausik task done ...` via the CLI (Bash tool), not the MCP tool — CLI invocations are fresh processes with no staleness and no MCP-layer timeout.
