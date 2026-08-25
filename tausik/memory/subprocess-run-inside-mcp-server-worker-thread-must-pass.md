---
slug: subprocess-run-inside-mcp-server-worker-thread-must-pass
title: "subprocess.run() inside MCP server worker thread MUST pass stdin=DEVNULL — root cause of task_done_v2 silent 10s hang"
type: gotcha
tags:
  - hang
  - mcp
  - stdio
  - subprocess
  - task_done
  - verify
  - windows
task: null
edges: []
---

SYMPTOM: tausik_task_done_v2 (and other MCP tools) appears to hang for 10+ seconds with no output. Diagnostic tools (tausik_self_check) show NO drift, no stale modules, no sibling MCPs.

ROOT CAUSE: subprocess.run() with capture_output=True does NOT redirect stdin. The child inherits parent's stdin. Inside the MCP project server's asyncio.to_thread worker, stdin is the JSON-RPC pipe to the IDE. When git (or any subprocess) is spawned without stdin=DEVNULL, on Windows it can block trying to read from that pipe — paginator probe, credential prompt detection, terminal check, or just generic stdin handling — and waits until subprocess.run's timeout fires. The except branch then returns a defensive None/True, masking the hang as a "successful but slow" call.

EVIDENCE (session #51, verify_git_diff.py): probes showed `is_declared_consistent_with_git_diff` taking exactly 10016ms (= timeout × 1) inside MCP context but ~200ms when called from a normal Python script. Adding stdin=subprocess.DEVNULL dropped MCP-path task_done_v2 from 10031ms to 63ms — a 159× speedup. The previous 5-day investigation patched diagnostics (self_check, wmic→PowerShell) without finding this root.

RULE: every subprocess.run() / Popen() in code that may execute inside the MCP project server (anything in scripts/ excluding scripts/hooks/) MUST pass stdin=subprocess.DEVNULL unless it explicitly needs to feed the child stdin. Hooks (scripts/hooks/) spawn from Claude Code IDE directly, not from the MCP server, so the risk is lower but the pattern is still safer to apply uniformly.

DETECTION: grep for `subprocess\.(run|Popen)\(` and look for any without `stdin=`. If the call could be reached from a tausik MCP tool handler, fix it. Hooks are lower priority but should follow the same convention.

RELATED FILES PATCHED: scripts/verify_git_diff.py (git log + git diff), scripts/project_service.py (session_metrics spawn), scripts/project_cli_extra.py (git branch --show-current), scripts/skill_manager.py (git pull/clone, pip install).
