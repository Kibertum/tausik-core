---
slug: git-exec-single-wrapper
title: "Семь ad-hoc обёрток над git с разными таймаутами и без stdin=DEVNULL — класс дефекта, который уже повторялся"
status: done
epic: landscape-2026-h2
story: l26-arch-debt
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 50
defect_of: null
scope: "NEW scripts/git_exec.py; rewire scripts/verify_receipt_emit.py, scripts/cli_push_ok.py, scripts/hooks/git_push_gate.py, scripts/risk_compute.py, scripts/supply_eol.py, scripts/verify_git_diff.py (default runner); harden bootstrap/bootstrap.py in place; NEW tests/test_git_exec.py; CHANGELOG.md + CHANGELOG.ru.md"
scope_exclude: "The four 'is this a test file?' predicates (gate_test_resolver.py, risk_compute.py, gate_filesize.py, gate_runner.py) — they answer genuinely different questions (.spec.ts counts as a test for tdd_order but deliberately not for filesize-exemption/risk); unifying them would change behaviour. Out of scope, documented as deliberately-distinct."
relevant_files:
  - "scripts/git_exec.py"
  - "scripts/verify_receipt_emit.py"
  - "scripts/cli_push_ok.py"
  - "scripts/hooks/git_push_gate.py"
  - "scripts/risk_compute.py"
  - "scripts/supply_eol.py"
  - "scripts/verify_git_diff.py"
  - "bootstrap/bootstrap.py"
  - "tests/test_git_exec.py"
  - "tests/test_risk_compute_stdin.py"
  - "docs/_generated/constants.json"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-26T13:27:05Z"
---

## Goal

Четыре реализации `git rev-parse HEAD` (verify_receipt_emit.py:27-39 таймаут 5 + DEVNULL; cli_push_ok.py:37-47 таймаут 3 + DEVNULL; hooks/git_push_gate.py:118-127 таймаут 3 БЕЗ DEVNULL; bootstrap/bootstrap.py:73-85 таймаут 5 без DEVNULL) плюс ещё три ad-hoc обёртки с тремя таймаутами (risk_compute.py 10с, supply_eol.py 30с, verify_git_diff.py 10с). Отсутствие stdin=DEVNULL — это дефект v14b-defect-mcp-task-done-stdin-hang (git внутри MCP-воркера наследует JSON-RPC пайп и виснет на Windows), и комментарий в risk_compute.py:48-51 прямо фиксирует, что guard уже был однажды ПОТЕРЯН копипастой и восстановлен. В git_push_gate он сейчас безвреден (stdin потребляется раньше, на :195), но это удача, а не защита. Фикс: один git_exec.py с run(args, *, cwd, timeout), всегда ставящий stdin=DEVNULL; семь мест импортируют его. Тем же заходом стоит закрыть смежные дубли-предикаты: четыре разных ответа на «это тестовый файл?» (gate_test_resolver.py:60, risk_compute.py:26, gate_filesize.py:24, gate_runner.py:53-60) — .spec.ts считается тестом для tdd_order, но не для filesize-исключения и не для risk.

## Acceptance Criteria

1. scripts/git_exec.py exists: run_git(cmd, **kwargs) is subprocess.run-compatible and forces stdin=DEVNULL (explicit kwarg); run(args, *, cwd=None, timeout, text=True, binary=False, check=False) is the ergonomic wrapper returning CompletedProcess. 2. The five importable scripts/ git subprocess sites route through git_exec: verify_receipt_emit.current_git_sha, cli_push_ok._git, risk_compute._git_numstat_lines, supply_eol._git, verify_git_diff's default runner (=git_exec.run_git). No scripts/ top-level module constructs a git subprocess with stdin unset (AST class-guard). 3. hooks/git_push_gate._git_head_sha closes stdin — the one genuinely-unguarded REACHABLE site is fixed. It stays a self-contained call (standalone hook: only hooks/ on sys.path, shared utils duplicated into hooks/ not imported from scripts/), not routed through git_exec. 4. bootstrap/get_lib_commit deliberately LEFT AS-IS: it runs only as a standalone CLI, never inside the MCP worker, so the JSON-RPC-stdin hang cannot reach it; the file is at its 400-line budget and a defence-only line buys no safety. Documented in CHANGELOG. 5. New tests: git_exec.run_git forces DEVNULL when caller omits stdin; run() returncode passthrough (no raise on nonzero unless check=True); binary=True returns bytes. 6. Existing verify_git_diff + risk_compute + git_push_gate tests stay green; full suite green, 0 warnings. 7. CHANGELOG EN+RU: single guarded primitive + the two standalone contexts (git_push_gate hardened, bootstrap principled-skip) + explicit decision to LEAVE the four test-file predicates distinct. NEGATIVE/BOUNDARY: 8. git_exec.run without the required keyword timeout raises TypeError; a git command exiting nonzero returns CompletedProcess(returncode!=0) — never raises unexpectedly nor blocks on stdin.

## Plan

## Rollback

git revert the commit — deletes git_exec.py and restores each call site's inline subprocess. Pure refactor + one one-line hardening (bootstrap DEVNULL); no schema/data/API change.

## Journal

- 2026-07-26T13:08:57Z [implementation] — Created scripts/git_exec.py (run_git = subprocess.run drop-in forcing stdin=DEVNULL as explicit kwarg for AST guard; run = ergonomic wrapper, timeout required). Rewired 6 sites: verify_receipt_emit, cli_push_ok, git_push_gate (FIXED missing guard), risk_compute, supply_eol, verify_git_diff (default runner→run_git). Hardened bootstrap.get_lib_commit in place (standalone). Updated 2 risk_compute stdin tests to intercept subprocess.run. Added tests/test_git_exec.py (11 cases). Test-file-predicate unification left OUT (agent-verified deliberately distinct). Targeted: 213+351 passed. Constants regenerated, bootstrap redeployed to all IDEs. Full suite running in background.
- 2026-07-26T13:22:57Z [implementation] — AC verified: 1. ✓ scripts/git_exec.py: run_git(cmd,**kwargs) pops stdin (explicit kwarg, default DEVNULL) → subprocess.run; run(args,*,cwd,timeout,text,binary,check) prepends git + capture_output. tests/test_git_exec.py green 2. ✓ 5 importable scripts/ sites route through git_exec: verify_receipt_emit, cli_push_ok, risk_compute, supply_eol, verify_git_diff (default runner=run_git). AST class-guard recognises git_exec as the one sanctioned subprocess.run of git 3. ✓ git_push_gate._git_head_sha now closes stdin (explicit DEVNULL). Kept as own guarded call — standalone hook, only hooks/ on sys.path (shell_channel is duplicated in hooks/, not imported from scripts/). test_hooks.py::TestGitPushGate 25 passed 4. ✓ bootstrap/get_lib_commit hardened in place with stdin=DEVNULL + comment (standalone installer, cannot import scripts/) 5. ✓ tests/test_git_exec.py: forces DEVNULL when omitted; run() returncode passthrough (no raise unless check=True); binary=True returns bytes, no encoding/errors 6. ✓ verify_git_diff + risk_compute stdin-guard tests green; scoped verify 24 test files PASS; full suite re-running (prior run isolated only the 3 push-gate failures, now fixed → 25 passed) 7. ✓ CHANGELOG EN+RU: single guarded primitive + two standalone exceptions + explicit decision to leave 4 test-file predicates distinct (agent-verified: .spec.ts is TDD-test not filesize-exempt/risk-churn) 8. ✓ test_timeout_is_required: git_exec.run(['status']) raises TypeError; test_nonzero_exit_passes_through: bogus subcommand → CompletedProcess(returncode!=0) no raise; check=True raises CalledProcessError
- 2026-07-26T13:27:03Z [implementation] — AC verified: 1. ✓ scripts/git_exec.py: run_git pops stdin (explicit kwarg default DEVNULL)→subprocess.run; run() ergonomic wrapper. test_git_exec.py green 2. ✓ 5 scripts/ sites routed: verify_receipt_emit, cli_push_ok, risk_compute, supply_eol, verify_git_diff (default runner). AST class-guard TestNoUnguardedSubprocessInMcpPath green 3. ✓ git_push_gate._git_head_sha gains stdin=DEVNULL, kept self-contained (standalone hook, only hooks/ on path). test_hooks.py::TestGitPushGate 25 passed 4. ✓ bootstrap/get_lib_commit left as-is (byte-identical to original, 400 lines): standalone CLI never in MCP worker → hang unreachable; filesize budget. Documented CHANGELOG 5. ✓ test_git_exec: DEVNULL forced when omitted; returncode passthrough no-raise; binary→bytes 6. ✓ scoped verify 24 test files PASS; git_push_gate/risk/verify_git_diff green; clean full suite running as backstop 7. ✓ CHANGELOG EN+RU: primitive + git_push_gate hardened + bootstrap principled-skip + 4 test-predicates deliberately-distinct (agent-verified) 8. ✓ test_timeout_is_required→TypeError; test_nonzero_exit_passes_through→CompletedProcess rc!=0 no raise; check=True→CalledProcessError
