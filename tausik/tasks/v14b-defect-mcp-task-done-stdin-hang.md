---
slug: v14b-defect-mcp-task-done-stdin-hang
title: "Defect: MCP task_done_v2 hangs ~10s — subprocess.run() inherits MCP stdin pipe in git/git-diff path"
status: done
epic: v14-polish-quality
story: v14-polish-b-quality
complexity: simple
role: developer
stack: python
tier: light
call_budget: 25
defect_of: null
scope: "scripts/verify_git_diff.py, scripts/project_service.py, scripts/project_cli_extra.py, scripts/skill_manager.py, tests/test_verify_git_diff_stdin.py (NEW), CHANGELOG.md, CHANGELOG.ru.md"
scope_exclude: "scripts/hooks/* (lower priority — hooks spawn from IDE directly, not MCP worker), MCP server / handler code (already correct), bootstrap/*"
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-04T11:08:16Z"
---

## Goal

Eliminate the chronic 10-second silent hang of tausik_task_done_v2 via MCP. Root cause: subprocess.run() in verify_git_diff.py + 3 other scripts/*.py spawn git/etc. without stdin=subprocess.DEVNULL; under MCP server's asyncio.to_thread worker the child inherits the JSON-RPC stdin pipe and blocks until timeout=10s, then defensive except-branch masks the hang as a successful-but-slow result.

## Acceptance Criteria

1. scripts/verify_git_diff.py: both `git log --since=...` and `git diff --name-only HEAD` subprocess.run() calls pass `stdin=subprocess.DEVNULL`. With explanatory comment referencing this defect. 2. scripts/project_service.py session_end's session_metrics subprocess.run + scripts/project_cli_extra.py git-branch detection + scripts/skill_manager.py git pull/clone + pip install: all gain stdin=subprocess.DEVNULL. 3. Regression test: tests/test_verify_git_diff_stdin.py asserts subprocess.run is called with stdin=DEVNULL on the git probes (mocking subprocess.run, asserting kwargs). 4. Empirical end-to-end measurement recorded in task notes: MCP task_done_v2 timing before fix vs after fix (10031ms → 63ms, 159×). 5. Gotcha saved to project memory documenting the rule "subprocess inside MCP worker MUST pass stdin=DEVNULL". 6. Decision saved with rationale. 7. CHANGELOG bilingual ### Fixed entry under [Unreleased] Phase B with full context (5-day investigation history, root cause, scope of fix, measurement). 8. Verify --task + task done --ac-verified.

## Plan

[{"step": "Reproduce: instrument MCP server with timing probes; confirm 10s in is_declared_consistent_with_git_diff inside run_gates_with_cache (DONE)", "done": true}, {"step": "Patch scripts/verify_git_diff.py: add stdin=DEVNULL to both git subprocess.run calls + comment", "done": true}, {"step": "Patch scripts/project_service.py session_end: add stdin=DEVNULL to session_metrics spawn", "done": true}, {"step": "Patch scripts/project_cli_extra.py: add stdin=DEVNULL to git branch --show-current call", "done": true}, {"step": "Patch scripts/skill_manager.py: add stdin=DEVNULL to git pull, git clone, pip install calls", "done": true}, {"step": "Add regression test tests/test_verify_git_diff_stdin.py asserting stdin=DEVNULL via mocked runner", "done": true}, {"step": "Re-bootstrap to deploy fixes to .claude/scripts/, run end-to-end timing test (10031ms \u2192 63ms confirmed)", "done": true}, {"step": "ruff + pytest fast lane green", "done": true}, {"step": "CHANGELOG bilingual ### Fixed with full context", "done": true}, {"step": "tausik verify --task + task done --ac-verified", "done": true}]

## Rollback

## Journal

- 2026-05-04T11:04:45Z [planning] — Root cause: subprocess.run() with capture_output=True does NOT redirect stdin. Inside MCP server's asyncio.to_thread worker, stdin = JSON-RPC pipe. git inherits → blocks reading stdin → timeout fires at 10s → except branch returns defensive None → cache logic returns True (no mismatch) and proceeds → from caller's perspective task_done is "slow but successful". Diagnostic toolchain (tausik_self_check) DID NOT catch this — modules are fresh, no sibling MCPs. The 5-day investigation focused on stale modules / wmic / ps / mtime — all peripheral. Real cause was subprocess stdin inheritance pattern. Empirical measurement: 10031ms (BEFORE fix) → 63ms (AFTER stdin=DEVNULL). 159× speedup. 4 source files patched. Gotcha #88 saved with rule + detection recipe.
- 2026-05-04T11:08:16Z [planning] — AC verified: 1. ✓ scripts/verify_git_diff.py: both git log + git diff calls now pass stdin=subprocess.DEVNULL with explanatory comment. 2. ✓ scripts/project_service.py session_metrics + scripts/project_cli_extra.py git-branch + scripts/skill_manager.py (git pull/clone, pip install) all gain stdin=DEVNULL. 3. ✓ tests/test_verify_git_diff_stdin.py NEW: asserts subprocess.run kwargs contain stdin=subprocess.DEVNULL on both git probes. Test PASSES. 4. ✓ Empirical end-to-end measurement: BEFORE 10031ms, AFTER 63ms — 159× speedup confirmed via JSON-RPC harness against fresh MCP server (post-bootstrap). 5. ✓ Gotcha #88 saved: rule + detection recipe for subprocess inheriting MCP stdin. 6. ✓ Decision #56 saved: project-wide convention. 7. ✓ CHANGELOG.md + CHANGELOG.ru.md bilingual ### Fixed entry under [Unreleased] Phase B with full root-cause story (5-day investigation, peripheral patches, real cause, fix scope, 159× measurement, lesson). 8. ✓ pytest fast lane: 2742 passed, 7 skipped, 118 deselected (85s). Ruff clean on all 5 changed files. Root cause: subprocess.run() with capture_output=True does NOT redirect stdin. Inside MCP server's asyncio.to_thread worker, stdin = JSON-RPC pipe to IDE. git inherits, blocks reading, times out at 10s, except-branch returns defensive None, masking hang as cache=hit. Diagnostic toolchain (tausik_self_check) can't see this — modules fresh, no siblings. Detection: git_diff_consistent ALWAYS True under MCP context regardless of actual diff.
