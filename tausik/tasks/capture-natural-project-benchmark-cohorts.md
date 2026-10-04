---
slug: capture-natural-project-benchmark-cohorts
title: "Capture natural project work as benchmark cohorts"
status: done
epic: release-1111-proportional-assurance
story: release1111-project-benchmark
complexity: complex
role: developer
stack: python
tier: substantial
call_budget: 120
defect_of: null
scope: "Usage/observation schema and migrations; task/session boundary recording; accepted-task aggregation; cohort storage or deterministic projection; CLI/MCP cohort inventory; fixtures, upgrade tests, privacy tests, and EN/RU telemetry docs."
scope_exclude: "Do not launch benchmark tasks or model calls. Do not calculate API-equivalent USD in this task. Do not infer subscription quota consumption from project usage."
relevant_files:
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - "docs/_generated/doc-map.md"
  - "docs/en/architecture.md"
  - "docs/en/cli-tasks.md"
  - "docs/en/cost-telemetry.md"
  - "docs/en/team-state-in-git.md"
  - "docs/ru/architecture.md"
  - "docs/ru/cli-tasks.md"
  - "docs/ru/cost-telemetry.md"
  - "docs/ru/team-state-in-git.md"
  - "harness/claude/mcp/project/handlers_status.py"
  - "harness/claude/mcp/project/tools.py"
  - "scripts/backend_migrations.py"
  - "scripts/backend_migrations_v70.py"
  - "scripts/backend_migrations_v71.py"
  - "scripts/backend_schema.py"
  - "scripts/backend_schema_indexes.py"
  - "scripts/benchmark_cohort_render.py"
  - "scripts/benchmark_cohorts.py"
  - "scripts/model_pinning.py"
  - "scripts/project_backend.py"
  - "scripts/project_cli_metrics.py"
  - "scripts/project_parser_ops.py"
  - "scripts/renar_tc_premise.py"
  - "scripts/state_export.py"
  - "scripts/usage_codex_report.py"
  - "scripts/usage_kilo.py"
  - "tests/test_benchmark_cohorts.py"
scope_paths: []
scope_tools: []
assurance_profiles:
  - executable
  - migration
  - research
assurance_impact: "{\"blast_radius\":\"broad\",\"data_change\":\"non_destructive\",\"governance_boundary\":false,\"level\":\"high\",\"owner_escalation\":false,\"privileged\":false,\"reversibility\":\"conditional\",\"security_boundary\":false}"
depends_on: []
completed_at: "2026-10-03T16:35:46Z"
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

Automatically bind accepted task usage and quality evidence to the TAUSIK version and observed model configuration so a project accumulates comparable before-and-after upgrade cohorts without synthetic runs.

## Acceptance Criteria

AC-1 Each accepted task can be joined to the exact TAUSIK version and observed host, provider, model, reasoning effort, and speed mode in force during its work window; identity changes are preserved rather than collapsed. AC-2 Natural task observations retain response rounds, input, cached-input subset, cache-write, output, reasoning-output subset, tool calls, active duration, attempts/retries, verification outcome, review level/invocations, and attribution confidence without double counting token subsets. AC-3 Cohorts are formed automatically from real project work by TAUSIK version and model configuration; no synthetic task execution, paid repetition, prompt replay, or full version×model matrix is required. AC-4 Accepted means delivered done tasks with non-obsolete resolution and explicit task boundaries; failed attempts and review/rework overhead stay charged to the accepted task, while unattributed activity remains a visible separate bucket. AC-5 Missing counters, identity, task linkage, or quality evidence remain unknown and reduce reported coverage; absence never becomes zero. No raw prompts, responses, credentials, or transcript bodies enter the project benchmark store. AC-6 Fresh and upgraded databases preserve history and schema parity; legacy observations remain explicitly legacy/unclassified rather than being assigned a guessed TAUSIK version or model. AC-7 A compact CLI/MCP cohort inventory reports available versions/models, dates, sample sizes, attribution coverage, and quality maturity before any comparison is attempted.

## Plan

[{"step": "Map existing usage_events, Codex observations, task boundaries, model identity and quality records; define the minimal additive cohort schema.", "done": true}, {"step": "Record TAUSIK/runtime identity at task boundaries and join exact response/tool/attempt/review/verification observations without subset double counting.", "done": true}, {"step": "Build accepted-task cohort projection and visible unattributed/legacy buckets with privacy-preserving provenance.", "done": true}, {"step": "Expose cohort inventory through CLI/MCP and cover restart, upgrade, mixed identity, missing data and obsolete-task cases.", "done": true}, {"step": "Update telemetry docs and run migration parity, focused tests, dedupe audit and canonical verify.", "done": true}]

## Rollback

Revert the additive cohort schema, recorder/projection and CLI/MCP exposure together; migration rollback preserves prior usage history and classifies legacy rows without guessing identity.

## Journal

- 2026-10-03T09:13:40Z [planning] — Interview/specification: owner approved proportional assurance for 1.11.1. Policy must be technology-agnostic and optimize token spend by residual uncertainty after profile evidence. Project benchmark uses only natural work already performed; no paid/synthetic runs or mandatory version×model matrix. It must support longitudinal comparison after TAUSIK upgrades and naturally observed model changes. Monetary estimate is API-equivalent USD from a dated rate card; subscription quota remains separate and unattributed.
- 2026-10-03T15:35:06Z [implementation] — Architecture premise: use an additive response-level benchmark_observations ledger plus deterministic cohort projection. Response rows preserve identity changes and token-subset semantics; existing task/review/verification tables supply accepted-task quality without copying transcripts. Legacy rows stay NULL-version/unclassified rather than receiving guessed identity.
- 2026-10-03T15:48:00Z [implementation] — Step 1 done: mapped sessions/tasks, usage_events, native Codex/Kilo observation adapters, reviews and verification_runs. Defined additive schema v70: lifecycle pins exact TAUSIK version at start/done and benchmark_observations stores one privacy-safe normalized response per opaque source hash. Historical task versions remain NULL/legacy; cached-input and reasoning-output remain subsets rather than added totals. Focused behavior and migration parity: 156 passed; adapter/CLI/MCP slice: 96 passed.
- 2026-10-03T15:51:21Z [implementation] — Step 2 done: task lifecycle pins installed TAUSIK version at start/done; Codex and Kilo native readers persist only allowlisted normalized observations keyed by opaque response hash. Accepted-task projection joins exact response rounds and token subsets with attempts/retries, task-boundary duration, usage_events tool calls, latest verification outcome and latest structured review. Mixed runtime identities stay in distinct cohorts. Missing counters remain NULL. Focused integration slice: 148 passed.
- 2026-10-03T15:52:09Z [implementation] — Step 3 done: deterministic projection includes only delivered done tasks with resolution IS NULL; failed attempts and rework remain charged through the full task window. Exact observations for active/obsolete work are a visible unaccepted bucket; inexact work is a separate unattributed bucket. Legacy NULL versions remain legacy/unclassified. Coverage reports total accepted tasks and unobserved accepted tasks. Privacy test confirms prompt/response sentinel bytes never enter the DB; v70 upgrade leaves historical task versions NULL. Migration/projection slice: 75 passed.
- 2026-10-03T15:53:24Z [implementation] — Step 4 done: metrics cohorts and tausik_metrics view=cohorts expose the same compact inventory with versions, observed identity, dates, sample sizes, attribution coverage and quality maturity. Tests cover restart idempotence, v70 upgrade, mixed identities, missing counters, obsolete/inexact buckets and transport parity. bootstrap --ide all regenerated every supported host. Focused slice: 101 passed.
- 2026-10-03T16:10:48Z [implementation] — L3 rounds #50-#51 reproduced and fixed stale native-response refresh, cross-version misclassification, elapsed-as-active substitution, latest-only review overhead, unknown-as-zero attempts/review invocations, lost identity provenance, mixed-identity double charging, and exact attribution to missing tasks. Focused migration/cohort suite: 54 passed; live DB migrated 70→71 after invalid benchmark FKs were downgraded to project attribution.
- 2026-10-03T16:34:53Z [implementation] — Updated EN/RU telemetry and architecture docs; migration/schema parity, focused behavior suites, pytest dedupe audit, independent L3 review #52, and canonical verify #3426 passed.
- 2026-10-03T16:35:09Z [implementation] — AC-1 PASS: exact task joins, per-field provenance, distinct model identities and start/done version boundaries are covered; cross-version windows stay unclassified. AC-2 PASS: response/token subsets, measured active duration, tools, attempts, cumulative review/verify runs and unsplit mixed-identity overhead are covered without subset double count. AC-3 PASS: native Codex/Kilo reads automatically upsert natural observations; 6334 existing Codex responses imported; no paid, synthetic, replay or model-matrix run. AC-4 PASS: obsolete/unfinished/inexact work is excluded; all rework stays charged once, with ambiguous task evidence in unsplit_task_evidence. AC-5 PASS (negative/privacy): missing counters, duration, attempts, review provenance, identity and task links remain null and lower coverage; unknown task slug downgrades to project attribution; secret prompt/response sentinel bytes are absent from DB. AC-6 PASS: v70/v71 fresh, upgrade and index parity passed; live DB upgraded 70→71; legacy rows remain unclassified; orphan links repair without data deletion. AC-7 PASS: CLI metrics cohorts and MCP cohorts expose matching compact inventory; MCP surface ratchet passed. Verification: #3426, 4523 passed, 18 skipped, 30 deselected across 241/657 mapped files; dedupe 0 COPY/282 PARALLEL and 7829/7829 able to fail; different-model L3 #52 approved with zero findings.
- 2026-10-03T16:35:33Z [implementation] — AC-1 (exact version and model identity): ✓ tests/test_benchmark_cohorts.py::test_capture_is_idempotent_private_and_uses_boundary_version ✓ tests/test_benchmark_cohorts.py::test_cross_version_work_window_stays_unclassified ✓ tests/test_benchmark_cohorts.py::test_identity_changes_form_distinct_cohorts_without_losing_task_cost AC-2 (natural metrics and overhead): ✓ tests/test_benchmark_cohorts.py::test_quality_and_retry_maturity_join_existing_evidence ✓ tests/test_benchmark_cohorts.py::test_unsplit_review_total_requires_evidence_for_every_mixed_task AC-3 (automatic natural capture): ✓ tests/test_benchmark_cohorts.py::test_project_capture_survives_restart_without_duplicate ✓ tests/test_benchmark_cohorts.py::test_finalized_native_response_updates_partial_observation AC-4 (accepted-task boundary and rework): ✓ tests/test_benchmark_cohorts.py::test_obsolete_and_inexact_work_never_enters_accepted_cohorts ✓ tests/test_benchmark_cohorts.py::test_unsplit_review_total_requires_evidence_for_every_mixed_task AC-5 (negative, unknown and privacy): ✓ tests/test_benchmark_cohorts.py::test_missing_values_and_legacy_identity_stay_unknown ✓ tests/test_benchmark_cohorts.py::test_elapsed_boundaries_and_missing_attempts_stay_unknown ✓ tests/test_benchmark_cohorts.py::test_unknown_task_attribution_is_downgraded_without_fk_damage AC-6 (fresh and upgraded schema): ✓ tests/test_benchmark_cohorts.py::test_v70_upgrade_keeps_legacy_tasks_unclassified ✓ tests/test_schema_upgrade_parity.py::TestColumnOrderDivergence::test_order_drift_is_confined_to_known_tables AC-7 (CLI/MCP inventory): ✓ tests/test_benchmark_cohorts.py::test_cli_and_mcp_expose_the_same_inventory ✓ tests/test_benchmark_cohorts.py::test_cli_renders_inventory_and_mcp_schema_advertises_it Green verification_run #3426; L3 review #52 approved.
- 2026-10-03T16:35:57Z [done] — Domain: real project import retained 6334 natural Codex observations and rendered cohorts without transcript bodies; the live DB migrated 70→71 and remains FK-clean. Negative: version-crossing work, missing counters/duration/attempts/review provenance, obsolete work, unknown task slugs, partial native responses and mixed identities all fail closed to unknown, excluded or unsplit states rather than false exact/zero values.
