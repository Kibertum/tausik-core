---
slug: verify-task-done-via-mcp-can-race-against-auto-format-hook
title: "verify+task_done via MCP can race against auto-format hook → cache git-mismatch"
type: gotcha
tags:
  - cache
  - mcp
  - race-condition
  - task-done
  - verify
task: null
edges: []
---

Sequence: tausik_verify (passes, status=miss) → tausik_task_done immediately after → blocking_failures with cache_status=git-mismatch. Reason: between the two MCP calls the harness can fire PostToolUse handlers (auto_format etc.) that touch staged files, invalidating the verify cache key (a git-fingerprint hash). Workaround: run both atomically via CLI shell — `.tausik/tausik verify --task <slug> && .tausik/tausik task done <slug> --ac-verified` — single shell process, nothing fires between the two commands. Already encountered twice with --ac-verified MCP path; CLI path always closes cleanly. Keep CLI as the canonical close path until MCP-side serialization improves.
