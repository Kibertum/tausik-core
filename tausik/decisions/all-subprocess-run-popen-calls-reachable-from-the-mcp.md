---
slug: all-subprocess-run-popen-calls-reachable-from-the-mcp
task: null
date: "2026-05-04"
edges: []
---

## Decision

All subprocess.run/Popen calls reachable from the MCP project server's worker thread MUST pass stdin=subprocess.DEVNULL. Hooks (scripts/hooks/) are lower priority but follow the same convention for uniformity.

## Rationale

Session #51 root-cause investigation of the chronic 5-day "task_done_v2 hangs" issue: probes traced 10016ms of dead time to subprocess git calls in scripts/verify_git_diff.py inheriting the MCP server's JSON-RPC stdin pipe and blocking until timeout=10s. Adding stdin=DEVNULL eliminated the hang (10031ms → 63ms, 159×). Previous patches (tausik_self_check diagnostics, wmic→PowerShell fallback) addressed peripheral symptoms; this is the actual root. The rule is cheap (one parameter) and guards against an entire class of bugs that are extremely hard to diagnose because the timeout makes the subprocess succeed defensively, hiding the issue from logs.
