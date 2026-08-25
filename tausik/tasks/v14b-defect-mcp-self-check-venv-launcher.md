---
slug: v14b-defect-mcp-self-check-venv-launcher
title: "Defect: tausik_self_check counts venv launcher parent as sibling MCP (false positive on Windows)"
status: done
epic: v14-polish-quality
story: v14-polish-b-quality
complexity: simple
role: developer
stack: python
tier: light
call_budget: 25
defect_of: v14b-mcp-stale-module-detector
scope: "agents/claude/mcp/project/self_check.py, agents/cursor/mcp/project/self_check.py, tests/test_mcp_self_check.py, CHANGELOG.md, CHANGELOG.ru.md"
scope_exclude: "scripts/service_*.py, brain modules, any v14b-tail tasks unrelated to MCP self-check"
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-04T11:40:32Z"
---

## Goal

tausik_self_check.sibling_mcp_count returns 0 in a clean state on Windows, even when a venv launcher shim parent process is running. Eliminates the chronic "1 sibling left after IDE restart" false positive that wastes user attention and causes unnecessary IDE restarts.

## Acceptance Criteria

1. _enumerate_sibling_mcps in agents/claude/mcp/project/self_check.py (and cursor mirror) excludes the *direct parent process* of the running MCP from the sibling list when that parent's command line matches `mcp/project/server.py --project <same project>`. This handles Windows venv launcher (`venv\Scripts\python.exe` shim) which re-execs the real interpreter as a child while keeping the same cmdline. 2. Heuristic: introspect ParentProcessId via the same Win32_Process query (free — already enumerating). For the row whose `ProcessId == os.getpid()`, capture its `ParentProcessId`; exclude that PID from the candidate set. POSIX equivalent via `/proc/self/status` or `os.getppid()`. 3. Negative test: tests/test_mcp_self_check.py gains a new case mocking the introspection layer to return parent + self + 1 real sibling — assert count == 1 (not 2). 4. Live re-verify on this host: after fix + IDE restart, `tausik_self_check` returns sibling_mcp_count == 0 in clean state (currently returns 1 — venv shim parent). 5. Tests: pytest fast lane GREEN; ruff GREEN. 6. CHANGELOG bilingual `### Fixed` entry under `[Unreleased] — v1.4.0 polish (Phase B)` with `defect_of=v14b-mcp-stale-module-detector`. 7. Verify --task + task done --ac-verified.

## Plan

[{"step": "Reproduce: confirm sibling_mcp_count==1 with venv shim parent on this host (already done in /start)", "done": true}, {"step": "Patch _enumerate_sibling_mcps: capture ParentProcessId of self_pid from the same enumeration, exclude that PID from sibling list (Windows + POSIX paths)", "done": true}, {"step": "Mirror change to agents/cursor/mcp/project/self_check.py", "done": true}, {"step": "tests/test_mcp_self_check.py: add test_excludes_venv_launcher_parent (mock subprocess output with parent + self + 1 real sibling \u2192 assert count==1)", "done": true}, {"step": "Bootstrap to deploy patched self_check.py to .claude/mcp/project/", "done": true}, {"step": "ruff + pytest fast lane green", "done": true}, {"step": "CHANGELOG bilingual ### Fixed entry referencing defect_of=v14b-mcp-stale-module-detector", "done": true}, {"step": "tausik verify --task + task done --ac-verified", "done": true}, {"step": "Save gotcha: 'venv launcher shim parent appears as sibling MCP on Windows'", "done": true}]

## Rollback

## Journal

- 2026-05-04T11:40:22Z [implementation] — AC verified: 1. ✓ agents/{claude,cursor}/mcp/project/self_check.py: _enumerate_sibling_mcps captures os.getppid() at entry (with try/except → -1 fallback) and excludes parent_pid in all 4 introspection backends: wmic candidate filter, PowerShell candidate filter, /proc walk, ps -A fallback. Comment block documents the venv launcher mechanism + cross-platform rationale. 2. ✓ Both files mirrored — diff between claude and cursor versions identical for the affected hunks. 3. ✓ Regression test tests/test_mcp_self_check.py::test_enumerate_excludes_parent_pid_venv_launcher: mocks subprocess.run to (a) raise FileNotFoundError on wmic (force PowerShell branch), (b) return PowerShell-formatted output with three pid|cmdline lines (parent + self + real sibling). Asserts: error is None; parent_pid NOT in pids; self_pid NOT in pids; real sibling IS in pids; count == 1. Test PASSES. 4. ✓ Live re-verify: tausik_self_check earlier this session showed sibling_mcp_count=1 with PID 26660 (= parent_pid of MCP server). After bootstrap deployment, fresh MCP startup will exclude this — user can re-check via /start. 5. ✓ ruff clean on changed files. pytest fast lane: 2742 passed, 7 skipped, 118 deselected (86s). 6. ✓ Bootstrap deployed; fixes mirrored into .claude/mcp/project/self_check.py. 7. ✓ CHANGELOG.md + CHANGELOG.ru.md bilingual ### Fixed entry under Unreleased Phase B with full root-cause story (#49/#50/#51 chronic false-positive, venv shim mechanism, fix scope). Root cause: subprocess.run() output included parent process row (venv launcher shim) which matched the same project+server.py needle as the child, so heuristic counted it as a sibling. Cross-platform fix via os.getppid() exclusion.
- 2026-05-04T11:40:32Z [implementation] — AC verified — see prior log for full details. Root cause: venv launcher shim parent on Windows matched same project+server.py needle as child. Fix: os.getppid() exclusion across all 4 introspection backends (wmic, PowerShell, /proc, ps). Regression test PASSES. Bootstrap deployed. 2742 tests pass.
