---
slug: mcp-server-freshness-diagnosed-via-mtime-snapshot-at
task: v14b-mcp-stale-module-detector
date: "2026-05-03"
edges: []
---

## Decision

MCP-server freshness diagnosed via mtime-snapshot at startup, exposed as `tausik_self_check`, surfaced through `/start` Phase 3 as ⚠ MCP Health

## Rationale

Three gotchas (#77, #79, #80) describe silent hangs in tausik_verify / tausik_task_done_v2 with the same root cause — the running MCP server holds stale Python modules because either (a) service-layer code was edited between MCP boot and the call, or (b) prior IDE windows leaked sibling MCP project servers. Other approaches considered: (1) PID-based health-gate killing stale servers — rejected, too destructive on a shared host; (2) recompile-on-edit MCP supervisor — rejected, complex + breaks IDE-managed lifecycle; (3) HARDER 60s envelope timeout — rejected, doesn't help servers loaded BEFORE the envelope code was added. Mtime snapshot is read-only, opt-in (only checked when /start asks), cross-platform (wmic/proc/ps fallbacks), and surfaces sibling-MCP leaks as a side benefit. Activates only after one IDE restart from deploy.
