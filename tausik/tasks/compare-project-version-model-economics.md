---
slug: compare-project-version-model-economics
title: "Compare project economics across TAUSIK versions and models"
status: done
epic: release-1111-proportional-assurance
story: release1111-project-benchmark
complexity: complex
role: developer
stack: python
tier: substantial
call_budget: 120
defect_of: null
scope: "Project benchmark comparison service; API-equivalent rate-card support reusing existing usage normalization; CLI/MCP reports and durable snapshot artifact; quality joins; statistical/negative fixtures; EN/RU user documentation."
scope_exclude: "Do not add a paid benchmark runner, synthetic task corpus execution, subscription-dollar attribution, account-quota allocation, or a single composite productivity score. Do not claim version/model causality from observational cohorts."
relevant_files:
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - "docs/en/cli-tasks.md"
  - "docs/en/cost-telemetry.md"
  - "docs/ru/cli-tasks.md"
  - "docs/ru/cost-telemetry.md"
  - "harness/claude/mcp/project/handlers_status.py"
  - "harness/claude/mcp/project/tools.py"
  - "scripts/benchmark_compare.py"
  - "scripts/benchmark_compare_cli.py"
  - "scripts/benchmark_compare_support.py"
  - "scripts/project_cli_metrics.py"
  - "scripts/project_parser_ops.py"
  - "tests/test_benchmark_compare.py"
  - "tests/test_benchmark_cohorts.py"
scope_paths: []
scope_tools: []
assurance_profiles: []
assurance_impact: null
depends_on: []
completed_at: "2026-10-04T09:01:52Z"
resolution: null
resolution_reason: null
tracker_refs: []
started_model_id: null
started_model_version: null
done_model_id: null
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
---

## Goal

Provide an honest project-level scorecard comparing naturally observed cohorts by TAUSIK version and model on tokens, rounds, API-equivalent USD and quality, while refusing causal or zero-cost claims when attribution or sample coverage is insufficient.

## Acceptance Criteria

AC-1 CLI and MCP compare two naturally observed project cohorts selected by TAUSIK version, model configuration, or explicit time labels; comparing TAUSIK versions on a stable model and comparing naturally used models on one version are supported, but a complete Cartesian benchmark is never required. AC-2 Each cohort reports sample size and coverage plus median/p90 response rounds, tool calls, active duration, attempts/retries, total input, cached input, uncached input, output, reasoning subset, and total non-double-counted tokens. AC-3 API-equivalent USD uses a dated, sourced provider/model rate card with separate uncached-input, cached-input, and output rates; unknown/stale/missing prices yield unknown cost. Subscription credits, included quota, and API-equivalent USD are never conflated. AC-4 The scorecard reports quality beside cost: verification failure/retry rate, L1/L2/L3/deep review mix and reviewer invocations, confirmed review findings, and downstream defect escapes only after a declared maturation window. It does not collapse these into an opaque universal efficiency score. AC-5 Results are stratified by complexity and assurance profile/impact. Pooled comparisons disclose task-mix differences; insufficient samples or changed model/settings return inconclusive rather than a savings or causality claim. AC-6 The report can persist a reproducible snapshot containing query, source coverage, rate-card provenance, TAUSIK versions, model identities, cohort membership hashes, and generated_at, without raw conversation content. AC-7 Negative fixtures cover mixed models, version changes mid-task, duplicate response records, obsolete tasks, missing prices, immature defect windows, and cohorts below the sample threshold. AC-8 EN/RU docs show the intended workflow: work normally on one version, upgrade, accumulate the next natural cohort, then compare; no paid benchmark run is requested.

## Plan

[{"step": "Define comparison eligibility, minimum sample and maturation rules; reuse existing exact usage and dated price-card contracts.", "done": true}, {"step": "Implement stratified cohort comparison for tokens, rounds, calls, duration, retries, review overhead and API-equivalent USD.", "done": true}, {"step": "Join quality signals and render an honest scorecard with coverage, task-mix warnings and inconclusive states instead of a composite score.", "done": true}, {"step": "Persist reproducible comparison snapshots and expose CLI/MCP workflows for before/after TAUSIK upgrades and naturally observed model cohorts.", "done": true}, {"step": "Validate adversarial fixtures, document EN/RU usage, run scoped/canonical verification, and capture the first natural 1.11.0\u21921.11.1 baseline when enough work exists.", "done": true}]

## Rollback

Revert comparison/reporting commands and snapshot writer; source task and usage telemetry stays intact, and no operational workflow depends on generated comparison artifacts.

## Journal

- 2026-10-03T09:13:40Z [planning] — Interview/specification: owner approved proportional assurance for 1.11.1. Policy must be technology-agnostic and optimize token spend by residual uncertainty after profile evidence. Project benchmark uses only natural work already performed; no paid/synthetic runs or mandatory version×model matrix. It must support longitudinal comparison after TAUSIK upgrades and naturally observed model changes. Monetary estimate is API-equivalent USD from a dated rate card; subscription quota remains separate and unattributed.
- 2026-10-04T08:48:40Z [implementation] — Step 1 done: comparison eligibility requires homogeneous exact version/model/settings, minimum natural sample, and declared defect maturation. Dated API-equivalent USD rate cards require source, as_of, valid_until and separate uncached/cached/output rates; missing, invalid, stale or unknown-model rates remain unknown.
- 2026-10-04T08:48:40Z [implementation] — Step 2 done: benchmark_compare aggregates natural accepted observations per task, then reports median/p90 plus coverage for rounds, calls, active duration, attempts/retries, input/cached/uncached/output/reasoning and non-double-counted total tokens. Version-only and model-only observational comparisons are supported without a Cartesian matrix.
- 2026-10-04T08:48:40Z [implementation] — Step 3 done: scorecards report verify failures/retries, L1/L2/L3/deep review mix, reviewer invocations, confirmed critical/high findings, matured defect escapes, complexity/profile/impact strata and pooled task-mix warnings. No composite efficiency or causal claim is emitted.
- 2026-10-04T08:52:22Z [implementation] — Step 4 done: CLI metrics compare and MCP tausik_metrics view=comparison accept version/model/settings/time selectors and optional snapshot path. Snapshot omits task slugs, retains selector/coverage/rate provenance/exact identities/membership hashes/generated_at. Live natural model cohorts (24 gpt-5.6-sol tasks, 13 gpt-5.6-terra tasks) were saved locally but correctly remain inconclusive because historical task boundaries lack exact TAUSIK version; API-equivalent USD remains unknown because no dated API rate card is configured.
- 2026-10-04T09:00:52Z [implementation] — Verification: focused comparison/MCP/docs slice passed 105 with 1 skipped; ruff passed; audit_pytest_dedupe reported 0 COPY, 282 PARALLEL and 7829 of 7829 tests able to fail. Canonical verify run 3429 passed 1385 tests, 16 skipped and 19 deselected across 52 of 658 mapped test files with 24 direct-import subject tests; 8 gates passed and hadolint was not applicable.
- 2026-10-04T09:00:53Z [implementation] — Domain evidence: the real project ledger contains 6489 natural observations. The first comparison used 24 gpt-5.6-sol accepted tasks and 13 gpt-5.6-terra accepted tasks and persisted .tausik/reports/natural-model-baseline-2026-10-04.json. It remained inconclusive because historical task boundaries have no exact TAUSIK version; tool calls and active duration stayed unknown where unmeasured; API-equivalent USD stayed unknown because no dated API card is configured. Negative evidence: mixed models, cross-version task windows, duplicate responses, obsolete tasks, missing and stale prices, immature defect windows, small cohorts, missing version identity, token subset arithmetic, task-mix differences and mixed identity dimensions all fail closed to excluded, unknown or inconclusive states instead of zero, savings or causality.
- 2026-10-04T09:01:11Z [implementation] — Step 5 done: adversarial fixtures, EN/RU workflow, scoped tests, dedupe audit, bootstrap deployment, live natural baseline and canonical verify are complete.
- 2026-10-04T09:01:12Z [implementation] — AC-1 PASS: CLI metrics compare and MCP tausik_metrics view=comparison select two natural cohorts by exact version, observed model/settings or ISO time bounds; tests test_version_comparison_reports_task_distributions_price_quality_and_strata, test_cli_accepts_version_model_and_time_selectors, test_time_selector_normalizes_z_and_offset_timestamps and test_mcp_comparison_uses_the_same_service prove version, model, time and transport paths without a Cartesian matrix. AC-2 PASS: per-task aggregation reports sample and coverage plus median/p90 rounds, tool calls, measured active duration, attempts, retries, input, cached input, derived uncached input, output, reasoning subset and total input-plus-output; the happy-path test proves cached and reasoning subsets are not double-counted, and the live 24/13 task report preserves unknown call/duration coverage. AC-3 PASS: api_equivalent_usd_rate_card requires source, as_of, valid_until, USD-per-million unit and separate uncached-input, cached-input and output rates; happy-path pricing proves the three-part sum, while test_duplicates_obsolete_missing_and_stale_prices_never_become_zero proves absent and stale cards remain null. Subscription credits and included quota are separate null fields. AC-4 PASS: scorecards expose verification failure/retry rates, L1/L2/L3/deep mix, reviewer invocations, confirmed critical/high findings and matured defect escapes; test_immature_defect_window_is_unknown_and_snapshot_omits_members proves immature windows stay unknown and no composite score exists. AC-5 PASS: complexity, assurance profile and impact strata plus task-mix warnings are emitted; parametrized ineligible-cohort fixtures and exact-identity comparison rules return inconclusive for small, mixed, incomplete or multi-dimension changes, with an explicit observational no-causality boundary. AC-6 PASS: persist_snapshot stores query, coverage, dated rate provenance, exact identities, generated_at and SHA-256 membership hashes while removing task names; the snapshot privacy test and the real .tausik/reports/natural-model-baseline-2026-10-04.json prove the path. AC-7 PASS: parametrized and boundary fixtures cover mixed models, version changes mid-task, duplicate response upserts, obsolete exclusion, missing/stale prices, immature defects and below-threshold cohorts; all fail closed. AC-8 PASS: docs/en/cost-telemetry.md, docs/ru/cost-telemetry.md and both cli-tasks mirrors describe normal work, upgrade, natural accumulation and comparison, and explicitly forbid paid repeats, synthetic corpora, prompt replay and a mandatory version-by-model matrix. Verification: run 3429 PASS, 1385 passed, 16 skipped, 19 deselected, 52 of 658 mapped files, 24 direct subject tests; focused slice 105 passed and 1 skipped; ruff clean; pytest dedupe 0 COPY and 7829 of 7829 tests able to fail.
- 2026-10-04T09:01:43Z [implementation] — AC-1: ✓ tests/test_benchmark_compare.py::test_version_comparison_reports_task_distributions_price_quality_and_strata; ✓ tests/test_benchmark_compare.py::test_cli_accepts_version_model_and_time_selectors; ✓ tests/test_benchmark_compare.py::test_time_selector_normalizes_z_and_offset_timestamps; ✓ tests/test_benchmark_compare.py::test_mcp_comparison_uses_the_same_service. CLI/MCP support natural exact version, model configuration and explicit time cohorts without a mandatory matrix. AC-2: ✓ tests/test_benchmark_compare.py::test_version_comparison_reports_task_distributions_price_quality_and_strata. Per-task median/p90 and coverage include all required counters; total is input plus output, not token subsets. AC-3: ✓ tests/test_benchmark_compare.py::test_version_comparison_reports_task_distributions_price_quality_and_strata; ✓ tests/test_benchmark_compare.py::test_duplicates_obsolete_missing_and_stale_prices_never_become_zero. Dated sourced three-rate API USD is separate from subscription/quota and unknown never becomes zero. AC-4: ✓ tests/test_benchmark_compare.py::test_immature_defect_window_is_unknown_and_snapshot_omits_members; ✓ tests/test_benchmark_compare.py::test_version_comparison_reports_task_distributions_price_quality_and_strata. Quality is reported beside cost with maturation, never collapsed into a universal score.
- 2026-10-04T09:01:43Z [implementation] — AC-5: ✓ tests/test_benchmark_compare.py::test_ineligible_natural_cohorts_are_inconclusive[below-sample-left-below-minimum-sample]; ✓ tests/test_benchmark_compare.py::test_ineligible_natural_cohorts_are_inconclusive[mixed-model-left-mixed-version-or-model-settings]. Complexity/profile/impact strata and mix warnings are present; insufficient/confounded cohorts are inconclusive. AC-6: ✓ tests/test_benchmark_compare.py::test_immature_defect_window_is_unknown_and_snapshot_omits_members. Snapshot retains query, coverage, rate provenance, identities, membership hashes and generated_at without task names or conversation content. AC-7: ✓ tests/test_benchmark_compare.py::test_ineligible_natural_cohorts_are_inconclusive[version-crossing-left-below-minimum-sample]; ✓ tests/test_benchmark_compare.py::test_duplicates_obsolete_missing_and_stale_prices_never_become_zero; ✓ tests/test_benchmark_compare.py::test_immature_defect_window_is_unknown_and_snapshot_omits_members. Negative fixtures cover every declared boundary. AC-8: ✓ tests/test_changelog_gate.py::TestDualChangelogRequirement::test_en_ru_both_changed_passes. EN/RU telemetry and CLI docs require normal work then upgrade and natural accumulation; they prohibit paid/synthetic/replay/matrix runs.
- 2026-10-04T09:01:52Z [implementation] — AC verified: 1-8 PASS with resolvable node IDs in the two preceding task logs. Domain: 6489 natural observations; 24 gpt-5.6-sol and 13 gpt-5.6-terra accepted tasks; historical missing TAUSIK version keeps the real snapshot inconclusive. Negative: mixed/cross-version/duplicate/obsolete/missing-price/stale-price/immature/small samples fail closed. Verification run 3429: 1385 passed, 16 skipped, 19 deselected over 52 of 658 mapped files; focused 105 passed, 1 skipped; ruff clean; dedupe 0 COPY.
