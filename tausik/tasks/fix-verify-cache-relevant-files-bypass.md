---
slug: fix-verify-cache-relevant-files-bypass
title: "Cross-check relevant_files against git diff"
status: done
epic: v134-hardening
story: security-fixes
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 60
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/verify_git_diff.py"
  - "scripts/service_verification.py"
  - "scripts/service_gates.py"
  - "scripts/gate_qg0_score.py"
  - "scripts/project_cli_verify.py"
  - "tests/test_service_verification.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-28T12:55:06Z"
---

## Goal

Refuse verify cache when declared relevant_files is a strict subset of files actually modified since task_start. Prevents agent from misreporting files to skip security-sensitive check. Closes HIGH (Sec).

## Acceptance Criteria

1. is_cache_allowed: query git diff --name-only HEAD since task created_at; 2. Refuse cache if declared relevant_files is strict subset of actually changed; 3. Test simulates agent declaring docs/x.md while editing scripts/auth.py; 4. Negative: misreporting files no longer yields stale-green; 5. Fallback when not in git repo: skip the cross-check (don't break non-git users).

## Plan

[{"step": "\u041d\u0430\u0439\u0442\u0438 is_cache_allowed \u0432 service_verification.py \u0438\u043b\u0438 verification_runs", "done": true}, {"step": "\u0421\u043f\u0440\u043e\u0435\u043a\u0442\u0438\u0440\u043e\u0432\u0430\u0442\u044c helper changed_files_since(task_created_at) \u2014 git diff --name-only HEAD@{task.created_at}", "done": true}, {"step": "\u0414\u043e\u0431\u0430\u0432\u0438\u0442\u044c cross-check: \u0435\u0441\u043b\u0438 set(declared_relevant) \u0440\u0430\u0432\u043d\u044b strict subset \u043e\u0442 set(actually_changed) \u2014 cache MISS, \u043b\u043e\u0433-warning", "done": true}, {"step": "Fallback: not in git repo OR git command fails \u2192 skip cross-check (\u043d\u0435 \u0431\u043b\u043e\u043a\u0438\u0440\u0443\u0435\u043c non-git users)", "done": true}, {"step": "\u0422\u0435\u0441\u0442 1: declared=docs/x.md, actually_changed=scripts/auth.py \u2192 cache refused", "done": true}, {"step": "\u0422\u0435\u0441\u0442 2: declared=scripts/auth.py, actually_changed=scripts/auth.py + tests/test_auth.py \u2192 cache allowed (declared \u2208 changed, \u043d\u043e \u043d\u0435 strict subset \u0440\u0430\u0437\u043b\u0438\u0447\u043d\u044b\u0445 \u0444\u0430\u0439\u043b\u043e\u0432? \u2014 \u0443\u0442\u043e\u0447\u043d\u0438\u0442\u044c \u0441\u0435\u043c\u0430\u043d\u0442\u0438\u043a\u0443)", "done": true}, {"step": "\u0422\u0435\u0441\u0442 3: not in git repo (no .git \u0432 tmp_path) \u2192 cross-check skipped, cache works \u043f\u043e \u043e\u0431\u044b\u0447\u043d\u044b\u043c \u043f\u0440\u0430\u0432\u0438\u043b\u0430\u043c", "done": true}, {"step": "task log + task done --ac-verified + commit 'fix(verify-cache): cross-check relevant_files vs git diff'", "done": true}]

## Rollback

## Journal

- 2026-04-28T12:31:13Z [implementation] — Plan: add changed_files_since(task_created_at, root) helper using git log --since + git diff HEAD; combined set. Add is_declared_consistent_with_git_diff(declared, task_created_at, root) predicate. Plumb task_created_at through run_gates_with_cache. Update cmd_verify too. Tests: 3 new in test_service_verification.py + integration test for run_gates_with_cache.
- 2026-04-28T12:42:58Z [implementation] — Implementation complete. service_verification: changed_files_since(timestamp, root, runner) + is_declared_consistent_with_git_diff(declared, timestamp, root, runner). run_gates_with_cache: new task_created_at param; before cache lookup, refuse if declared ⊊ actually changed (status='git-mismatch'). Plumbed task.created_at from service_gates._run_quality_gates and project_cli_verify.cmd_verify. Tests: 16 new (7 changed_files_since branches, 7 is_declared_consistent branches, 3 integration with run_gates_with_cache), all 99 in test_service_verification.py pass. Full suite: 2287 passed +1 skipped (was 2270).
- 2026-04-28T12:43:23Z [implementation] — AC verified: ✓1 is_cache_allowed kept pure (security-only); new is_declared_consistent_with_git_diff queries `git log --since=<task_created_at> --name-only --pretty=format:` + `git diff --name-only HEAD`, unions, normalizes paths (forward slashes, leading ./ stripped). ✓2 Cache refused when declared_set strict subset of actual_set (i.e. actual_set - declared_set non-empty). Status reported as 'git-mismatch' for telemetry. ✓3 Test test_under_declared_returns_false simulates docs/x.md declared while scripts/auth.py actually changed → returns False (cache refused). ✓4 Test test_cache_refused_when_declared_underreports: pre-warmed cache then re-runs with extra git-changed file not in declared → status='git-mismatch' instead of 'hit'. ✓5 Test test_not_in_git_returns_true: tmp_path without .git → predicate returns True (skip cross-check, defensive). Plus test_returns_none_when_no_git_dir, test_returns_none_when_subprocess_raises, test_returns_none_when_git_log_fails — all return None gracefully. Knowledge captured: pattern saved as memory linked to upstream blind-review story. Full pytest: 2287 passed, +17 vs v1.3.3 baseline.
- 2026-04-28T12:54:56Z [implementation] — AC verified: ✓1 New verify_git_diff.py: changed_files_since(timestamp,root,runner) calls `git log --since=<task_created_at> --name-only --pretty=format:` + `git diff --name-only HEAD`, unions, normalizes paths. ✓2 is_declared_consistent_with_git_diff refuses cache when actual_set - declared_set is non-empty (under-declaration → strict subset). Status='git-mismatch' surfaces in run_gates_with_cache return tuple. ✓3 test_under_declared_returns_false: declared=[docs/x.md], actually changed=scripts/auth.py → False. ✓4 test_cache_refused_when_declared_underreports: pre-warm cache then re-run with extra git-changed file → status='git-mismatch'. ✓5 test_not_in_git_returns_true (tmp_path without .git) + test_returns_none_when_no_git_dir + test_returns_none_when_subprocess_raises + test_returns_none_when_git_log_fails — all defensive fallback paths covered. Refactor: extracted helpers to verify_git_diff.py (149 lines) and qg0_dimensions_score to gate_qg0_score.py (47 lines) for filesize-gate compliance (service_verification 398, service_gates 381, both under 400). Full suite: 2287 passed +1 skipped (was 2270). 16 new tests in test_service_verification.py.
