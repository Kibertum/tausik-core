---
slug: v153-windows-wrapper-and-rag-fixes
title: "[P0] Windows fixes: cmd-wrapper unconditional exit + RAG reserved-name walk abort"
status: done
epic: null
story: null
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: v151-public-release-readiness
scope: "bootstrap/tausik_wrapper.cmd, bootstrap/tausik_wrapper.sh, harness/claude/mcp/codebase-rag/rag_detect.py, harness/cursor/mcp/codebase-rag/rag_detect.py (mirror), tests/"
scope_exclude: "no API changes; no behavior change beyond the two fixes"
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-15T10:13:37Z"
---

## Goal

Two Windows defects to land permanently with tests. (1) CRITICAL regression: bootstrap/tausik_wrapper.cmd — an unescaped ')' inside the echo text of the `if not defined SCRIPTS (...)` block closes the block early, so `exit /b 1` runs UNCONDITIONALLY → the .tausik/tausik.cmd wrapper fails with exit 1 on every command after bootstrap. Fix: escape the parens (^(...^)) or rewrite to goto; verify tausik_wrapper.sh has no analogous issue. (2) harness codebase-rag rag_detect.get_file_list — a path component that is a Windows reserved device name (con/prn/aux/nul/com1-9/lpt1-9, with or without extension) makes os.path.relpath raise ValueError, which propagates and aborts the whole os.walk → the code index is silently empty. Fix: _RESERVED_DOS_NAMES frozenset + _is_reserved_name helper; prune reserved dirs, skip reserved files, wrap both relpath calls in try/except ValueError: continue. Mirror into the cursor harness copy if present. Both additive, no API change.

## Acceptance Criteria

AC1: tausik_wrapper.cmd — the literal parens in the no-scripts error echo are escaped (^( ^)) (or replaced by goto), so `if not defined SCRIPTS` is a real conditional and `exit /b 1` only runs when no scripts dir exists. AC2: tausik_wrapper.sh confirmed free of an analogous escaping bug. AC3: a smoke test runs the generated wrapper with a valid SCRIPTS dir → exit 0 + python invoked (passthrough); negative: no scripts dir → exactly one error line + exit 1. AC4: rag_detect adds _RESERVED_DOS_NAMES + _is_reserved_name; get_file_list prunes reserved dirs, skips reserved files, and wraps BOTH os.path.relpath in try/except ValueError: continue — preserving the v1.5.2 max_seconds deadline + _is_reparse_or_symlink logic. AC5: a test builds a temp tree containing a reserved-name component → get_file_list does NOT raise and returns the other files (on non-Windows, simulate by monkeypatching relpath to raise ValueError for the reserved path). AC6: fix mirrored into harness/cursor/mcp/codebase-rag/rag_detect.py if it exists (parity). AC7: full pytest green; ruff+mypy clean; filesize<400. Negative: the cmd wrapper does NOT exit 1 when a scripts dir exists; get_file_list does NOT abort the whole walk on a single reserved-name ValueError.

## Plan

## Rollback

git revert; both fixes are localized + additive.

## Journal

- 2026-06-15T10:12:10Z [implementation] — Root cause: (D1) wrapper.cmd regression I introduced in v151 qwen-loop — literal '(...)' in the no-scripts echo closed the `if not defined SCRIPTS (...)` block early → `exit /b 1` ran unconditionally on every command. (D2) Windows reserved device names (con/prn/aux/nul/com1-9/lpt1-9, with/without ext) make os.path.relpath raise ValueError, which aborted the whole os.walk → silently-empty RAG index. Prevention: (D1) wrapper now uses `goto :noscripts` (no inline block to break) + explicit `exit /b %ERRORLEVEL%` to propagate python's code; smoke tests run the generated .cmd on Windows. (D2) _is_reserved_name pruning + defensive try/except ValueError around both relpath calls; unit truth-table + ValueError-simulation tests. Both additive, no API change.
- 2026-06-15T10:12:23Z [implementation] — AC verified: 1. ✓ bootstrap/tausik_wrapper.cmd:16 — `if not defined SCRIPTS goto :noscripts`; error echo moved to :noscripts label (no inline block); regenerated .tausik/tausik.cmd verified (goto + exit /b %ERRORLEVEL%) 2. ✓ bootstrap/tausik_wrapper.sh — parens are inside a double-quoted echo (bash-safe), if/fi is a real conditional; no analogous bug 3. ✓ tests/test_wrapper_smoke.py — TestCmdWrapper.test_passthrough_exits_zero (exit 0 + STUB_OK passthrough) and test_missing_scripts_one_error_exit_one (exit 1, exactly one error line) RAN on Windows (os.name=nt) and pass 4. ✓ harness/claude/mcp/codebase-rag/rag_detect.py — _RESERVED_DOS_NAMES + _is_reserved_name added; get_file_list prunes reserved dirs, skips reserved files, both relpath in try/except ValueError: continue; max_seconds deadline + _is_reparse_or_symlink preserved 5. ✓ tests/test_mcp_windows.py::TestReservedDosNames — truth_table, reserved_files_and_dirs_skipped, relpath_valueerror_does_not_abort_walk (monkeypatched relpath ValueError) all pass 6. ✓ harness/cursor/mcp/codebase-rag/rag_detect.py — identical fix mirrored (was byte-identical at HEAD) 7. ✓ full pytest 4348 passed (262s); ruff `All checks passed!`; mypy `Success: no issues found in 210 source files`; changed files 281/281/278/109/30 lines (all <400). Doc-constants resynced (test_count 4341→4348) in constants.json + README badge/x2
- 2026-06-15T10:13:37Z [implementation] — AC verified: 1. ✓ bootstrap/tausik_wrapper.cmd:16 goto :noscripts; regenerated .tausik/tausik.cmd verified 2. ✓ tausik_wrapper.sh — parens inside double-quoted echo (bash-safe), real if/fi 3. ✓ tests/test_wrapper_smoke.py TestCmdWrapper passthrough+negative RAN on Windows, pass 4. ✓ rag_detect.py _RESERVED_DOS_NAMES+_is_reserved_name; prune+skip+try/except both relpath; deadline/_is_reparse preserved 5. ✓ test_mcp_windows.py::TestReservedDosNames 3 tests incl monkeypatched ValueError pass 6. ✓ harness/cursor/mcp/codebase-rag/rag_detect.py mirrored 7. ✓ full pytest 4348 passed; ruff clean; mypy 210 files clean; all changed files <400; constants.json+README test_count resynced 4341->4348
- 2026-06-15T10:13:46Z [done] — Root cause (regression): tausik_wrapper.cmd had literal parens in an echo inside `if not defined SCRIPTS (...)`, closing the block early so `exit /b 1` ran unconditionally; introduced in the v151 qwen-loop edit. Prevention: use `goto :label` instead of inline if-blocks containing punctuation, + Windows .cmd smoke test in CI. (Second defect — edge-case: reserved DOS names make os.path.relpath raise ValueError aborting os.walk; prevention: per-entry try/except + _is_reserved_name pruning.) Domain: verified outside tests — regenerated .tausik/tausik.cmd runs real commands exit 0; RAG walk indexes real trees containing reserved-name siblings without empty index.
