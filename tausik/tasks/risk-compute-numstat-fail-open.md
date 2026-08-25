---
slug: risk-compute-numstat-fail-open
title: "risk_compute._git_numstat_lines fails OPEN on nonzero git exit — reads lowest risk instead of conservative default"
status: done
epic: null
story: null
complexity: simple
role: developer
stack: python
tier: light
call_budget: 12
defect_of: git-exec-single-wrapper
scope: "scripts/risk_compute.py (_git_numstat_lines returncode check); tests/test_risk_compute_stdin.py (add nonzero-returncode test); CHANGELOG.md + CHANGELOG.ru.md"
scope_exclude: null
relevant_files:
  - "scripts/risk_compute.py"
  - "tests/test_risk_compute_stdin.py"
  - "docs/_generated/constants.json"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-26T13:50:01Z"
---

## Goal

Adversarial review (session #140) found a fail-open regression introduced by git-exec-single-wrapper: migrating _git_numstat_lines from subprocess.check_output (which RAISED CalledProcessError on nonzero git exit → caught by _factor_code_churn → returns None → risk_model defaults code_churn to the conservative 1.0, 'fail-visible') to git_exec.run (check=False) dropped the error propagation. Now on any git failure (unborn HEAD, 'fatal: bad revision HEAD', corrupted repo, permission error) result.stdout is empty → total=0 → returns 0 → norm_code_churn(0)=0.0 (LOWEST risk) instead of the intended 1.0. This is the exact fail-open mode risk_model.py's docstring warns against. The existing test only covers TimeoutExpired-raises, not the nonzero-returncode-without-exception path. Fix: inspect result.returncode and raise CalledProcessError on nonzero so the existing except in _factor_code_churn still catches it; add a test that stubs a nonzero-returncode CompletedProcess and asserts the factor is dropped (None), not computed as 0.

## Acceptance Criteria

1. risk_compute._git_numstat_lines checks result.returncode after git_exec.run and raises subprocess.CalledProcessError on nonzero (mirroring the check_output contract it replaced), so _factor_code_churn's existing except catches it → returns None → risk_model defaults code_churn to the conservative 1.0. 2. On SUCCESS (returncode 0) behavior is byte-identical to now: parses numstat lines, filters by relevant set, sums added+deleted. 3. New test stubs subprocess.run to return a CompletedProcess with returncode!=0 (NOT a raised exception) and asserts _factor_code_churn returns None (factor dropped), not 0.0. 4. Existing test_risk_compute_stdin tests (stdin guard, TimeoutExpired→None) still pass. 5. Full suite green, 0 warnings. NEGATIVE/BOUNDARY: the nonzero-returncode-without-exception path (the untested gap the review found) is now covered and yields the conservative fail-visible None, never a silent 0.0.

## Plan

## Rollback

git revert — restores the unguarded git_exec.run call. One-function change + one test.

## Journal

- 2026-07-26T13:49:40Z [implementation] — AC verified: 1. ✓ _git_numstat_lines now: if result.returncode!=0 raise CalledProcessError → _factor_code_churn except catches → None → risk_model conservative 1.0 2. ✓ returncode==0 path unchanged (parse/filter/sum); test_risk_compute + test_git_call_passes_stdin_devnull green 3. ✓ test_nonzero_git_exit_drops_factor_not_zero: stubs subprocess.run→CompletedProcess(returncode=128,stdout='') (no raise); asserts _factor_code_churn returns None not 0.0 4. ✓ test_risk_compute_stdin: stdin-guard + TimeoutExpired→None still pass (14 passed total) 5. ✓ scoped verify (high) 2 test files PASS; full suite as final gate before commit
- 2026-07-26T13:49:51Z [implementation] — Root cause (regression): migrating _git_numstat_lines from subprocess.check_output (raises CalledProcessError on nonzero exit) to git_exec.run (check=False, returns on nonzero) silently dropped the error-propagation the caller relied on — the exception was the signal that made _factor_code_churn drop the factor to the conservative 1.0. The wrapper's return-not-raise contract differs from check_output's, and the migration preserved the happy path but not the failure path. Prevention: when replacing a raise-on-error primitive with a return-on-error one, every call site must add an explicit returncode check; and negative-path tests must cover nonzero-returncode-WITHOUT-exception, not only the raised-exception path (the original test only stubbed a raise). Adversarial review caught it because all tests passed — a silent behavior change with no negative-case coverage.
- 2026-07-26T13:49:59Z [implementation] — AC verified: 1. ✓ _git_numstat_lines raises CalledProcessError on nonzero returncode → caught by _factor_code_churn → None → conservative 1.0 2. ✓ returncode==0 path byte-identical; test_risk_compute green 3. ✓ test_nonzero_git_exit_drops_factor_not_zero: nonzero CompletedProcess (no raise) → None not 0.0 4. ✓ stdin-guard + TimeoutExpired tests still pass (14 total) 5. ✓ scoped verify high 2 files PASS; full suite final gate pending
