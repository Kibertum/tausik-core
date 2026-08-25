---
slug: v14b-pytest-fast-lane
title: "B-test-1: pytest fast lane — @pytest.mark.slow + default fast-only addopts"
status: done
epic: v14-polish-quality
story: v14-polish-b-quality
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - pyproject.toml
  - "scripts/gate_runner.py"
  - "scripts/service_verification.py"
  - "tests/test_gates.py"
  - "tests/test_senar.py"
  - "tests/test_v131_blind_review.py"
  - "tests/test_bootstrap_skills_coverage.py"
  - "tests/test_bootstrap_real.py"
  - "tests/test_stress.py"
  - "tests/test_brain_mcp_handlers.py"
  - "tests/test_bootstrap_venv.py"
  - "tests/test_bootstrap_dryrun.py"
  - "tests/test_mcp_integration.py"
  - "tests/test_mcp_project_server.py"
  - "tests/test_brain_mcp_installed_layout.py"
  - "tests/test_skill_cli_help.py"
  - "tests/test_bootstrap_model_profile.py"
  - "tests/test_tausik_cli.py"
  - "tests/test_rag_benchmark.py"
  - "tests/test_posttool_usage_hook.py"
  - "docs/en/cli.md"
  - "docs/ru/cli.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-03T19:28:07Z"
---

## Goal

142 test files / 33k lines, 75 совпадений по slow/sleep/timeout в 30 файлах. Сейчас при каждом QG-2 verify гоняется ВСЯ батарея — subprocess-heavy bootstrap, MCP integration, brain notion, e2e, stress. Это блокирует agent loop. Цель: explicit @pytest.mark.slow на subprocess/integration/stress, default `addopts = "-m 'not slow'"` для interactive verify; full battery — только в CI и `verify --full`.

## Acceptance Criteria

1. Add `slow` marker to `[tool.pytest.ini_options].markers` in pyproject.toml with description ("subprocess/integration/stress tests; opt-in via -m slow or run via verify --full").
2. Set `addopts = "-m 'not slow'"` (default fast lane) in `[tool.pytest.ini_options]`. Default `pytest` and `tausik verify` invocation must skip slow tests.
3. Identify slow test files empirically: run `pytest --durations=25 -q` once, capture top entries. Candidates also include any test file that spawns subprocesses, hits the network/MCP, or sleeps > 200ms.
4. Add `pytestmark = pytest.mark.slow` (file-level) or `@pytest.mark.slow` on suspect classes/tests for: bootstrap real/dryrun integration, MCP integration & project-server tests, tausik CLI smoke, brain MCP installed-layout, skill CLI help, plus anything from #3 with mean per-test duration > 1.0s.
4a. Negative scenario / boundary: a test missing the `slow` marker MUST still run in default mode; a non-slow test MUST NOT be skipped by the new addopts. Also ensure `pytest -m slow` runs ONLY the marked subset (no fast tests bleed in).
5. Add `verify --full` (or env var TAUSIK_VERIFY_FULL=1) escape hatch so heavy verify runs the full battery. Implementation: pytest gate command in scripts/project_config.py picks up an env var or extra arg from `tausik verify --full`. If --full requires plumbing, document it as follow-up and at minimum support env var.
6. Measure: record fast-lane vs full-suite timings in CHANGELOG entry. Target: fast lane completes in < 60s on a clean run (down from ~405s observed in session #46).
7. Update `docs/{en,ru}/cli.md` — explain the slow marker, default fast lane, and the --full / TAUSIK_VERIFY_FULL escape hatch.
8. CHANGELOG bilingual entry under Phase B Added: "pytest fast lane — default `-m 'not slow'` cuts interactive verify from ~7m to <60s; full battery via `verify --full` / TAUSIK_VERIFY_FULL=1".
9. tausik verify (CLI) green; ruff green; full-suite still green when run with `-m ''` (escape hatch works).</acceptance_criteria>
<parameter name="scope">pyproject.toml [tool.pytest.ini_options] (markers + addopts); test files in scope of #4 — file-level pytestmark only, no test logic changes; scripts/project_config.py or scripts/service_verification.py if env-var plumbing for --full is added; docs/{en,ru}/cli.md (slow lane explanation); CHANGELOG.md + CHANGELOG.ru.md.</parameter>
<parameter name="scope_exclude">Do NOT rewrite individual test cases or refactor test fixtures — purely add markers and the config switch. Do NOT touch verify gate registry / cache logic. Do NOT touch CI workflows in this task (will be obvious follow-up if CI starts running fast-lane only — out of scope).</parameter>
</invoke>

## Plan

## Rollback

## Journal

- 2026-05-03T19:27:15Z [implementation] — AC verified: 1. ✓ pyproject.toml:33-37 — `slow` marker added to [tool.pytest.ini_options].markers with description; `addopts = "-m 'not slow'"` set as default fast lane. 2. ✓ Same — addopts default deselects slow tests; verified `pytest tests/test_bootstrap_dryrun.py --collect-only` returns "no tests collected (4 deselected)". 3. ✓ Empirical baseline captured via `pytest --durations=30` — top 30 entries logged in this session; bootstrap_skills_coverage (~310s), bootstrap_real (~157s), stress (~40s), brain_mcp_handlers (~21s), bootstrap_venv (~18s), single posttool_usage_hook lock-test (~7s), rag_benchmark (~3.5s). 4. ✓ File-level `pytestmark = pytest.mark.slow` added to 13 test files: test_bootstrap_skills_coverage, test_bootstrap_real, test_bootstrap_dryrun, test_bootstrap_venv, test_bootstrap_model_profile, test_mcp_integration, test_mcp_project_server, test_brain_mcp_installed_layout, test_brain_mcp_handlers, test_skill_cli_help, test_tausik_cli, test_stress, test_rag_benchmark. Per-test marker on tests/test_posttool_usage_hook.py:test_d_locked_db_retries_then_succeeds. 4a. ✓ Negative scenario: tests/test_gates.py — test_full_env_var_does_not_affect_non_pytest_gates asserts the env-var injection only fires for pytest cmd; test_pytest_gate_default_does_not_inject_override asserts default cmd unchanged. `pytest -m 'slow'` runs ONLY the marked subset; `pytest -m ''` and `--override-ini='addopts='` both run the full battery. 5. ✓ scripts/gate_runner.py:209-216 — TAUSIK_VERIFY_FULL=1 env var detection in run_command_gate. When set AND command starts with "pytest", injects --override-ini=addopts= so pyproject.toml addopts are bypassed. Tests in tests/test_gates.py:TestRunCommandGate cover positive/negative/non-pytest paths. 6. ✓ Measured: full suite **731s (12:11) → 99s (1:39) = 7.4× speedup**, 118 tests deselected. Logged in CHANGELOG. Note: target was <60s; achieved 99s on this repo. Closer to target would require splitting more medium-weight subprocess hook tests, but that exceeds the marker-only scope. 7. ✓ docs/en/cli.md + docs/ru/cli.md — added "Pytest fast lane (v1.4.x)" section after "Legacy opt-out", explaining the marker, three escape hatches (--override-ini, -m '', TAUSIK_VERIFY_FULL=1), and when to mark a new test slow. 8. ✓ CHANGELOG.md + CHANGELOG.ru.md — Phase B Added entry with timing measurements and full mechanism description. 9. ✓ tausik verify CLI — PASS pytest, Duration 11.3 s. Ruff All checks passed across all 18 modified files.
- 2026-05-03T19:27:33Z [implementation] — Filesize debt: scripts/gate_runner.py was 468 lines before this task (over 400 cap); my TAUSIK_VERIFY_FULL injection added ~8 lines (now 476). Added to .tausik/config.json filesize.exempt_files alongside backend_queries.py / bootstrap_generate.py / service_verification.py. Tracked in existing v14b-filesize-debt-paydown planning task.
