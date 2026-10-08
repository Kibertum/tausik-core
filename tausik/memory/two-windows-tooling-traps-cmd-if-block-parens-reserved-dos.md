---
slug: two-windows-tooling-traps-cmd-if-block-parens-reserved-dos
title: "Two Windows tooling traps: .cmd if-block parens + reserved DOS names abort os.walk"
type: gotcha
tags:
  - cmd-wrapper
  - os-walk
  - rag
  - v153
  - windows
task: v153-windows-wrapper-and-rag-fixes
edges: []
---

Two Windows-only defects fixed in v153 (both shipped to users as silent failures):

(1) .cmd if-blocks: a literal '(' or ')' in echo text INSIDE an `if cond (...)` block closes the block early — the rest runs unconditionally. tausik_wrapper.cmd's `if not defined SCRIPTS (echo ...(.claude/.cursor...)...; exit /b 1)` made `exit /b 1` fire on EVERY command. Fix pattern: never put bare parens in echo inside an inline block — use `goto :label` (no inline block) and put the echo at a top-level label, plus explicit `exit /b %ERRORLEVEL%` to propagate the child exit code. (.sh is immune: parens in a double-quoted echo are literal.)

(2) os.path.relpath raises ValueError on Windows when any path component is a reserved DOS device name (con/prn/aux/nul/com1-9/lpt1-9, with OR without an extension). An unguarded relpath inside os.walk aborts the WHOLE walk → silently-empty RAG index. Fix pattern: _is_reserved_name (stem before first dot, lower(), set-membership) to prune reserved dirs + skip reserved files, AND wrap every relpath in try/except ValueError: continue as defense-in-depth.

Generalizable: any os.walk that calls relpath/normpath must tolerate ValueError per-entry; any generated .cmd must keep punctuation out of inline if-block echoes.
