---
slug: venv-scripts-python-exe-is-a-launcher-shim-that-re-execs
title: "venv\\Scripts\\python.exe is a launcher shim that re-execs the real interpreter as a child on Windows"
type: gotcha
tags:
  - mcp
  - process-introspection
  - self_check
  - venv
  - windows
task: v14b-defect-mcp-self-check-venv-launcher
edges: []
---

On Windows, `venv\Scripts\python.exe` is NOT the actual Python interpreter — it's a tiny launcher binary that finds the real interpreter (per `pyvenv.cfg` `home=` field) and spawns it as a CHILD process. Both the launcher and the child appear as `python.exe` in tasklist, and Win32_Process reports the SAME `CommandLine` for both because Windows propagates the original spawn cmdline down the tree.

Practical implications:
- Any heuristic that enumerates `python.exe` processes by command-line pattern will see the launcher parent as a sibling of the actual worker. ALWAYS exclude the direct parent PID before counting.
- The launcher's ExecutablePath is `venv\Scripts\python.exe`; the worker's ExecutablePath is the absolute path to the system Python (e.g. `C:\Python311\python.exe`). Differentiating by ExecutablePath also works.
- Triggered chronic false positive in `tausik_self_check.sibling_mcp_count` — exhibits as "1 sibling left after IDE restart" that never goes away. See defect v14b-defect-mcp-self-check-venv-launcher.
- Pattern affects ALL three TAUSIK MCP servers spawned by Claude Code (project, brain, codebase-rag) — they all show shim+real pairs.
