---
slug: fix-stdin-hang-risk-in-resolve-assessor-git-subpro
title: "fix stdin-hang risk in resolve_assessor git subprocess"
status: done
epic: null
story: null
complexity: null
role: developer
stack: python
tier: null
call_budget: null
defect_of: fix-hardcode-assessor-identity
scope: "scripts/project_cli_renar.py (single subprocess.run call)"
scope_exclude: null
relevant_files:
  - "scripts/project_cli_renar.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-06-14T08:52:59Z"
---

## Goal

project_cli_renar.py:29 _git_user_name() calls subprocess.run(['git','config','user.name']) without stdin=DEVNULL — flagged by test_risk_compute_stdin as MCP-reachable stdin-hang risk. Defect introduced in #88 fix-hardcode-assessor-identity batch (uncommitted). Add stdin=subprocess.DEVNULL to close the hang vector and turn the suite green before committing the batch.

## Acceptance Criteria

AC-1: subprocess.run in _git_user_name() passes stdin=subprocess.DEVNULL — verified by reading project_cli_renar.py. AC-2: test_risk_compute_stdin::test_all_top_level_subprocess_calls_set_stdin passes (0 offenders) — verified via pytest. AC-3 (negative/boundary): when `git config user.name` is absent/errors (OSError/SubprocessError) OR the subprocess would otherwise block on stdin, _git_user_name() returns None instead of hanging — verified via existing resolve_assessor fallback tests (test_renar_assessor_resolve.py) staying green.

## Plan

## Rollback

git revert / remove the stdin=subprocess.DEVNULL kwarg

## Journal

- 2026-06-14T08:52:22Z [implementation] — Added stdin=subprocess.DEVNULL to _git_user_name() subprocess.run at project_cli_renar.py:29. Bootstrap re-run (scripts→.claude synced). Targeted: 12 passed (test_risk_compute_stdin + test_renar_assessor_resolve).
- 2026-06-14T08:52:30Z [implementation] — AC-1: ✓ subprocess.run now passes stdin=subprocess.DEVNULL — project_cli_renar.py:29-35. AC-2: ✓ test_risk_compute_stdin::test_all_top_level_subprocess_calls_set_stdin passes (0 offenders) — tested via tests/test_risk_compute_stdin.py. AC-3 (negative): ✓ git-absent/error path returns None without hanging — tested via tests/test_renar_assessor_resolve.py (fallback chain green). Suite: 12 passed targeted; verify standard passed (pytest gate).
- 2026-06-14T08:52:37Z [implementation] — Root cause: in #88, fix-hardcode-assessor-identity introduced a NEW subprocess.run (git config user.name) inside _git_user_name() but omitted stdin=subprocess.DEVNULL. The repo invariant — every MCP-reachable subprocess must close stdin to avoid a hang when the child inherits the server's stdin — is enforced by test_risk_compute_stdin, which wasn't re-run at that task's close (the batch was verified scoped, not full-suite). Fix: add stdin=subprocess.DEVNULL. Prevention: full-suite pytest before committing a multi-task batch (this session caught it pre-commit).
- 2026-06-14T08:52:42Z [implementation] — AC-1: ✓ subprocess.run passes stdin=subprocess.DEVNULL — project_cli_renar.py:29-35. AC-2: ✓ test_all_top_level_subprocess_calls_set_stdin passes (0 offenders) — tested via tests/test_risk_compute_stdin.py. AC-3 (negative): ✓ git-absent/error returns None without hanging — tested via tests/test_renar_assessor_resolve.py. 12 passed targeted; verify standard passed.
- 2026-06-14T08:52:59Z [implementation] — AC-1: ✓ subprocess.run passes stdin=subprocess.DEVNULL — project_cli_renar.py:29-35. AC-2: ✓ test_all_top_level_subprocess_calls_set_stdin passes (0 offenders) — tested via tests/test_risk_compute_stdin.py. AC-3 (negative): ✓ git-absent/error returns None without hanging — tested via tests/test_renar_assessor_resolve.py. 12 passed targeted; verify standard passed. Knowledge: memory #158 (gotcha).
