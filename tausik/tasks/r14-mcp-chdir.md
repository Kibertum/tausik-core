---
slug: r14-mcp-chdir
title: "MCP project server: chdir to --project, remove getcwd drift"
status: done
epic: rel-14-readiness
story: rel-14-audit-fixes
complexity: null
role: null
stack: null
tier: moderate
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-30T23:43:11Z"
---

## Goal

Release 1.4 readiness: r14-mcp-chdir

## Acceptance Criteria

1. agents/claude/mcp/project/server.py and agents/cursor/mcp/project/server.py call os.chdir(args.project) right after sys.path setup. 2. Behavior parity check: brain server already does chdir; project server now mirrors. 3. Negative scenario: when --project does not exist or is not a directory, server prints clear error to stderr and exits non-zero - does not silently chdir to garbage.

## Plan

## Rollback

## Journal

- 2026-04-30T23:43:11Z [implementation] — AC: 1. chdir present in both servers (verified via test_*_chdir_is_in_main). 2. Brain parity confirmed via reading brain/server.py:34-35. 3. Negative scenario: missing --project exits 2 with stderr 'is not a directory' (verified via test_*_rejects_missing_dir). All 4 tests pass.
- 2026-04-30T23:43:11Z [implementation] — Implemented chdir(args.project) with isdir guard (exit 2) in agents/claude/mcp/project/server.py and agents/cursor/mcp/project/server.py — parity with tausik-brain server.
