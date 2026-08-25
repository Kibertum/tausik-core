---
slug: try-except-doesn-t-catch-a-hang-compound-mcp-handlers
title: "try/except doesn't catch a HANG — compound MCP handlers (session_open) need per-section watchdogs"
type: gotcha
tags:
  - hang
  - mcp
  - session-open
  - start
  - v1.5.8
  - watchdog
  - windows
task: harden-session-open-watchdog
edges: []
---

tausik_session_open bundles 5 sub-calls for /start Phase 1, each wrapped in try/except. try/except catches EXCEPTIONS but NOT a blocked call. A sub-op that HANGS instead of raising (DB write contending with sibling MCP servers, a self_check subprocess wedged past its own timeout on Windows, a pathologically large repo) froze the whole envelope -> IDE stuck on 'Generating…' forever. Symptom is IDE-only: every sub-call and the whole handler complete in ~3s in isolation; the freeze only manifests under live multi-server contention (a project can have 6+ concurrent tausik-project servers, one per open Claude Code window). DIAGNOSTIC TRAP: piping JSON-RPC with a closed stdin makes the server EOF-exit BEFORE responding -> looks like exit=0 'success' but no result; hold stdin open (append `; sleep N`) to see real behavior. FIX (v1.5.8): _section_with_timeout runs each sub-call in a daemon thread, join(6s); on timeout returns {'error':'<section> timed out after 6s'} so /start degrades + names the culprit. Safe because conn is check_same_thread=False + busy_timeout=5000. Lesson: any compound handler that fans out to DB/subprocess must bound EACH branch, not rely on try/except. See [[subprocess-text-true-cp1252-windows]].
