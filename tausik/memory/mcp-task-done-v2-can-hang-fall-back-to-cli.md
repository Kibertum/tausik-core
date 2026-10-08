---
slug: mcp-task-done-v2-can-hang-fall-back-to-cli
title: "MCP task_done_v2 can hang — fall back to CLI"
type: gotcha
tags:
  - cli-fallback
  - hang
  - mcp
  - qg2
  - task-done
task: v14b-skill-core-cleanup
edges: []
---

MCP `tausik_task_done_v2` is the official close path, but it intermittently hangs (no response, no error) — observed in session #47 closing v14b-skill-core-cleanup with a long `evidence` string + 25 relevant_files. Companion to gotcha #77 (verify-side hang), which was scoped to edits-of service_verification.py / gate_runner.py — this one fired without those edits.

Workaround:
1. `.tausik/tausik task done <slug> --ac-verified` (CLI). Same QG-2 contract.
2. If CLI complains "no fresh verify run", re-run `.tausik/tausik verify --task <slug>` first — the MCP-side verify cache row sometimes does not satisfy the CLI lookup (different process / cwd handle).

Diagnostic signal: the task_done_v2 invocation simply never returns. Don't wait — abort, switch to CLI, save context.

Adopt: at session start, prefer CLI for `task done` of tasks with large evidence/relevant_files arrays; reserve MCP for compact closures.
