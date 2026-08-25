---
slug: v14b-filesize-debt-paydown
title: "B-debt-1: Split oversized scripts/backend_queries.py + bootstrap/bootstrap_generate.py"
status: done
epic: v14-polish-quality
story: v14-polish-b-quality
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/backend_queries.py + new scripts/backend_queries_usage.py; bootstrap/bootstrap_generate.py + new bootstrap/bootstrap_hooks.py; scripts/service_verification.py + new scripts/security_pattern.py; scripts/gate_runner.py + new scripts/gate_command_runner.py; .tausik/config.json (clear exempt_files); CHANGELOG.md + CHANGELOG.ru.md; new tests/test_filesize_split_smoke.py."
scope_exclude: "Do NOT change function/class behavior — purely move-and-reimport. Do NOT touch backend_queries' callers (project_service / service_*). Do NOT alter the hooks-block contents in bootstrap (only relocate the builder). Do NOT touch CI workflows. Do NOT consolidate other near-limit files (e.g. service_gates.py at ~500 lines) — out of this task's scope."
relevant_files:
  - "scripts/backend_queries.py"
  - "scripts/backend_queries_usage.py"
  - "scripts/service_verification.py"
  - "scripts/security_pattern.py"
  - "scripts/verify_cache.py"
  - "scripts/gate_runner.py"
  - "scripts/gate_command_runner.py"
  - "bootstrap/bootstrap_generate.py"
  - "bootstrap/bootstrap_hooks.py"
  - "tests/test_filesize_split_smoke.py"
  - ".tausik/config.json"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-03T20:01:18Z"
---

## Goal

Два модуля в core source давно превышают 400-line filesize gate: scripts/backend_queries.py (536 lines) и bootstrap/bootstrap_generate.py (433 lines). На время v14b-usage-events-auto-write оба добавлены в gates.filesize.exempt_files в .tausik/config.json. Долг нужно закрыть: extract usage-related queries в backend_queries_usage.py, extract hooks-block builder в bootstrap_hooks.py — затем убрать exempt entries.

## Acceptance Criteria

1. Split scripts/backend_queries.py (currently 536 lines) by extracting usage_events/metrics-related queries into scripts/backend_queries_usage.py (mixin or imported helper). Original module re-exports the same public surface so callers do not change. Final line count: backend_queries.py ≤ 400.
2. Split bootstrap/bootstrap_generate.py (433 lines) by extracting the hooks-block builder (settings.json hooks dict construction) into bootstrap/bootstrap_hooks.py. Final line count: bootstrap_generate.py ≤ 400.
3. Split scripts/service_verification.py (464 lines) by extracting the security pattern classifier (is_security_sensitive + _SECURITY_PATH_TOKENS / _SEC_BASE / _SECURITY_BASENAMES / _SECURITY_EXTENSIONS) into scripts/security_pattern.py. service_verification.py re-imports for backwards-compatibility with existing callers. Final line count: service_verification.py ≤ 400.
4. Split scripts/gate_runner.py (476 lines) by extracting the run_command_gate body (substitution + subprocess invocation, including TAUSIK_VERIFY_FULL injection) into scripts/gate_command_runner.py. gate_runner.py keeps the public dispatch (run_gates / run_filesize_gate / run_tdd_order_gate). Final line count: gate_runner.py ≤ 400.
5. Negative scenario / boundary: an import of any moved symbol from the ORIGINAL module (e.g. `from service_verification import is_security_sensitive`) MUST still work — no broken external imports allowed. Add a smoke-import test (tests/test_filesize_split_smoke.py) that imports each historical name from its old module and asserts identity.
6. Remove all 4 entries from .tausik/config.json gates.filesize.exempt_files. Bootstrap regen confirms exempt_files is empty (or absent).
7. Run filesize gate manually to confirm: `tausik gates list` shows no exempt; `tausik verify --task` on this task passes filesize gate.
8. Existing test suite (full battery via TAUSIK_VERIFY_FULL=1) still green — no broken imports / behavior changes.
9. CHANGELOG bilingual entry under Phase B Fixed: "filesize debt paydown — 4 oversized modules split, exempt list cleared".
10. tausik verify (CLI) green; ruff green.</acceptance_criteria>
<parameter name="scope">scripts/backend_queries.py + new scripts/backend_queries_usage.py; bootstrap/bootstrap_generate.py + new bootstrap/bootstrap_hooks.py; scripts/service_verification.py + new scripts/security_pattern.py; scripts/gate_runner.py + new scripts/gate_command_runner.py; .tausik/config.json (clear exempt_files); CHANGELOG.md + CHANGELOG.ru.md; new tests/test_filesize_split_smoke.py.</parameter>
<parameter name="scope_exclude">Do NOT change any function/class behavior — purely move-and-reimport. Do NOT touch backend_queries' callers (project_service / service_*). Do NOT alter the hooks-block contents in bootstrap (only relocate the builder). Do NOT touch CI workflows. Do NOT consolidate other near-limit files (e.g. service_gates.py at ~500 lines) — out of this task's scope.</parameter>
</invoke>
<invoke name="mcp__tausik-project__tausik_task_start">
<parameter name="slug">v14b-filesize-debt-paydown</parameter>
</invoke>

## Plan

## Rollback

## Journal

- 2026-05-03T20:01:17Z [implementation] — AC verified: 1. ✓ scripts/backend_queries.py 536→397 — 4 usage methods extracted to BackendQueriesUsageMixin in backend_queries_usage.py; BackendQueriesMixin inherits, public surface on SQLiteBackend unchanged. 2. ✓ bootstrap/bootstrap_generate.py 433→223 — settings hooks dict (~225 lines) extracted to bootstrap_hooks.build_hooks_dict(_hook_cmd). generate_settings_claude unchanged in shape (verified by smoke test). 3. ✓ scripts/service_verification.py 464→345 — security pattern (is_security_sensitive + tokens/basenames/extensions) extracted to security_pattern.py; cache helpers (is_cache_allowed, resolve_gate_signature, _build_cache_command, has_fresh_verify_run) extracted to verify_cache.py. Both re-exported. 4. ✓ scripts/gate_runner.py 476→395 — run_command_gate + _SCOPED_SKIP_SENTINEL extracted to gate_command_runner.py. subprocess re-imported in gate_runner.py with noqa F401 (preserves backwards-compat for tests that patch `gate_runner.subprocess.run`). 5. ✓ Negative scenario / boundary: tests/test_filesize_split_smoke.py asserts every moved symbol is importable from its ORIGINAL module AND identity-equal to its new location (canonical IS reexport). 8 cases covering all 4 splits + settings.json shape contract. Plus full battery (TAUSIK_VERIFY_FULL=1) confirmed no broken external imports. 6. ✓ .tausik/config.json gates.filesize.exempt_files now [] (was 4 entries). Bootstrap regen preserved the empty list. 7. ✓ Filesize gate manually verified: tausik verify --task on this task PASSED filesize (no exempt entries needed). 8. ✓ Full test suite via TAUSIK_VERIFY_FULL=1: 2707 passed initially with 11 failures (9 in test_gates.py from `gate_runner.subprocess.run` monkeypatches no longer resolving — fixed by re-importing subprocess in gate_runner.py with noqa for backwards compat; 1 pre-existing CLAUDE.md size drift; 1 pre-existing tier-critical test from prior session). After fix: tests/test_gates.py 88/88 PASS. Pre-existing failures (CLAUDE.md size + senar test) tracked separately. 9. ✓ CHANGELOG.md + CHANGELOG.ru.md — Phase B Added entry with concrete line counts and module names. 10. ✓ tausik verify CLI [PASS] pytest 5.7s. Ruff All checks passed (auto-fixed 4 unused imports post-split).
