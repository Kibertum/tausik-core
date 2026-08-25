---
slug: multiple-stale-mcp-project-servers-root-cause-of-task-done
title: "Multiple stale MCP project servers — root cause of task_done_v2 hang"
type: gotcha
tags:
  - envelope-timeout
  - mcp
  - process-leak
  - stale-modules
  - task-done
  - verify
task: null
edges: []
---

Investigated session #47: 3 pairs of MCP project servers running concurrently for [вычеркнуто: local-path] (PIDs 8712 from 16:58, 43904 from 19:30, 41596 from 23:07 — yesterday). Each VSCode/Claude window respawn leaves the previous MCP child unkilled.

Why this hangs `tausik_task_done_v2` (and possibly other MCP calls): when `service_verification.py` (mtime 22:48) and `gate_runner.py` (mtime 23:00) are modified between MCP startups, the OLDER servers (16:58, 19:30) hold stale Python modules. Stale modules predate v1.4 changes — including the extracted `security_pattern.py` / `verify_cache.py` / `gate_command_runner.py` re-exports AND possibly the envelope-timeout wrapper itself. Without envelope timeout, gates can run indefinitely.

Why CLI works: every CLI invocation reloads from disk (no module cache).

Diagnostic recipe:
1. `Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" | ? CommandLine -match '<project-path>.*mcp/project'` — list MCP servers.
2. Compare CreationDate against mtimes of `scripts/service_verification.py`, `scripts/gate_runner.py`, `scripts/service_gates.py`. Any MCP older than the youngest mtime is stale.
3. `verify_pipeline_timeout_seconds` in `.tausik/config.json` is NOT set on this project → falls back to DEFAULT_PIPELINE_TIMEOUT_S=60. Stale servers don't see this code path.

Workarounds (immediate):
- Kill all but the newest MCP project server pair before starting work. Restart IDE if unsure.
- Use `.tausik/tausik` CLI for `task done`, `verify` when MCP is suspect.
- Set `verify_pipeline_timeout_seconds: 60` explicitly in config — ensures NEW servers honor it; doesn't help stale ones.

Long-term fix candidates: PreToolUse hook that pings MCP server's `__startup_time` and warns if stale; or a SessionStart hook that kills MCP children with CreationDate older than newest source mtime.

Supersedes/extends gotchas #77 (verify hangs) and #79 (task_done_v2 hangs) — those described the symptoms; this one names the mechanism.
