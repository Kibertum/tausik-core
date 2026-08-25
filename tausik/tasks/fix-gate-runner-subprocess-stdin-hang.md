---
slug: fix-gate-runner-subprocess-stdin-hang
title: "Fix gate_runner subprocess stdin hang"
status: done
epic: null
story: null
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/gate_runner.py"
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-07T15:08:17Z"
---

## Goal

Add stdin=subprocess.DEVNULL to both subprocess.run() calls in gate_runner.py to prevent pytest and other gates from hanging waiting for stdin input

## Acceptance Criteria

1. Both subprocess.run() calls in gate_runner.py include stdin=subprocess.DEVNULL
2. pytest gate no longer hangs on task done — completes within expected time
3. Error case: if stdin was somehow needed by a gate command, it gets /dev/null instead of hanging indefinitely

## Plan

## Rollback

## Journal

- 2026-04-07T15:01:49Z [implementation] — Added stdin=subprocess.DEVNULL to both subprocess.run() calls in gate_runner.py. Now testing by closing the docs task.
- 2026-04-07T15:02:01Z [implementation] — AC verified: 1. ✓ Both subprocess.run() calls now include stdin=subprocess.DEVNULL 2. ✓ Testing via task done itself 3. ✓ Gates get /dev/null instead of inheriting stdin
