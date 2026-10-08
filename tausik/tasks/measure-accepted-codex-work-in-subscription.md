---
slug: measure-accepted-codex-work-in-subscription
title: "Measure accepted Codex work in subscription credits"
status: done
epic: null
story: null
complexity: medium
role: developer
stack: python
tier: substantial
call_budget: null
defect_of: null
scope: "Codex usage observation/reporting and configuration; credit-equivalent calculation only."
scope_exclude: "No API-dollar conversion, quota prediction, external paid runs, synthetic benchmark, model routing, commit, push, or release."
relevant_files:
  - "scripts/usage_credit.py"
  - "scripts/usage_codex_report.py"
  - "scripts/usage_observation.py"
  - "tests/test_usage_codex.py"
  - "tests/test_usage_observation.py"
  - "docs/en/codex-economy-baseline.md"
  - "docs/ru/codex-economy-baseline.md"
  - "docs/en/configuration.md"
  - "docs/ru/configuration.md"
  - ".tausik/config.json"
  - "changelog.d/codex-subscription-credit-metric-111.md"
scope_paths:
  - "scripts/usage_credit.py"
  - "scripts/usage_codex_report.py"
  - "scripts/usage_observation.py"
  - "tests/test_usage_codex.py"
  - "tests/test_usage_observation.py"
  - "docs/en/codex-economy-baseline.md"
  - "docs/ru/codex-economy-baseline.md"
  - "docs/en/configuration.md"
  - "docs/ru/configuration.md"
  - "changelog.d/codex-subscription-credit-metric-111.md"
  - ".tausik/config.json"
scope_tools: []
depends_on: []
completed_at: "2026-10-02T11:28:48Z"
resolution: null
resolution_reason: null
tracker_refs: []
started_model_id: gpt-6-astra
started_model_version: null
done_model_id: gpt-6-astra
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
---

## Goal

Report accepted-task consumption as raw Codex counters plus configurable credit-weighted cost, without conflating subscription credits, included quota, API dollars, or token totals.

## Acceptance Criteria

AC-1 A per-task report separately shows uncached input, cached input, cache writes, output/reasoning output, rounds, and credit-weighted total when a dated rate card is configured; output reasoning and cached input are never added twice. AC-2 Included quota and purchased subscription credits are never represented as API dollars, token totals, or guaranteed task counts; quota snapshots remain separate. AC-3 Rate cards are project configuration with source/date/unit metadata and no silently stale built-in subscription price; missing, malformed, partial, or unknown-model rates produce explicit unknown cost. AC-4 Existing Codex/portable fixtures cover cache subsets, missing counters, unknown models, mixed models and output-heavy work; no extra natural task is run solely for measurement. Negative: corrupt counters, missing source/date, negative rates, and unknown model prefixes fail closed to an unknown credit result without breaking raw telemetry.

## Plan

[{"step": "Define the subscription-credit normal form and dated configuration boundary", "done": true}, {"step": "Extend existing Codex observations and per-task report without a parallel telemetry path", "done": true}, {"step": "Verify cache, output, unknown-rate and no-dollar negative cases", "done": true}, {"step": "Feed the metric into 1.11 economy acceptance without changing its quality bar", "done": true}]

## Rollback

Revert credit-weighted reporting and configuration; raw Codex counters remain authoritative.

## Journal

- 2026-10-02T11:26:45Z [implementation] — Defined a dated project rate card with source/unit metadata and no framework default.
- 2026-10-02T11:26:45Z [implementation] — Extended the existing Codex observation/report path; raw counters remain authoritative and reasoning/cached subsets are not double-counted.
- 2026-10-02T11:26:45Z [implementation] — Focused verification covers missing metadata, negative/NaN rates, mixed and unknown models while preserving raw telemetry.
- 2026-10-02T11:26:49Z [implementation] — Logged the measured credit view into r111-economy-hardening-acceptance; its replay and quality acceptance remain intentionally unmet.
- 2026-10-02T11:27:37Z [implementation] — AC evidence: tests/test_usage_codex.py + tests/test_usage_observation.py: 42 passed; dedupe audit: 0 COPY, 282 PARALLEL; docs constants check OK. Live report: configured dated card; 30 accepted tasks, 29 measured / 1 explicit unknown; 2037.571 measured credits; raw input 526,421,076, cached input 514,842,368 (97.8%). Scoped verify #3365 PASS: 396 passed, 12 skipped, 7/657 test files. Verify #3364 was invalidated by stale MCP process after bootstrap and ran no pytest.
- 2026-10-02T11:27:47Z [implementation] — AC-1 verified by existing report path and focused tests: raw uncached/cached/cache-write/output/reasoning/round counters plus credit total, with subset fields priced once. AC-2 verified by explicit separation of quota, API USD, tokens, and credits in schema/docs. AC-3 verified by dated project rate card with source/unit, no built-in rate, and explicit unknown on malformed/partial/unknown models. AC-4 verified by existing fixtures: 42 focused tests passed; scoped verify #3365 passed 396 tests over 7/657 mapped files. Negative inputs fail closed without losing raw telemetry.
- 2026-10-02T11:28:10Z [implementation] — AC-1 counters and credit total verified without double counting. AC-2 quota, USD, tokens, and credits stay separate. AC-3 dated project rate card fails closed for invalid or unknown rates. AC-4 42 focused tests and scoped verify 3365: 396 passed across 7 of 657 mapped test files.
- 2026-10-02T11:28:27Z [implementation] — AC-1 (credit weighting without double counting): ✓ tests/test_usage_codex.py::test_report_accepts_only_db_done_tasks_and_persists_no_command AC-2 (quota remains separate): ✓ tests/test_usage_observation.py::test_quota_remains_separate_and_missing_is_unknown AC-3 (invalid and unknown rate cards fail closed): ✓ tests/test_usage_codex.py::test_report_accepts_only_db_done_tasks_and_persists_no_command AC-4 (native counters and subset semantics): ✓ tests/test_usage_observation.py::test_accepted_task_cost_deduplicates_and_does_not_add_token_subsets_twice Scoped verification: green verification_run #3365, 396 passed, 12 skipped, 7/657 mapped test files.
- 2026-10-02T11:28:34Z [implementation] — AC-1 through AC-4 verified by cited existing tests and green verification_run #3365: 396 passed across 7 of 657 mapped test files.
- 2026-10-02T11:28:39Z [implementation] — NO-DEAD-END: both red attempts were workflow/process refusals, not failed implementation approaches: #3364 used a stale MCP after redeploy; first closure lacked a resolvable pytest node-id citation. Fresh verify #3365 is green and exact node IDs are now logged.
- 2026-10-02T11:28:48Z [implementation] — AC-1 through AC-4 verified by cited existing tests and green verification_run #3365: 396 passed across 7 of 657 mapped test files.
