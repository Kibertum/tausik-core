---
slug: r111-cross-host-economy-acceptance
title: "1.11: prove economy on Codex and compatibility on GLM"
status: done
epic: release-111-economy-draft
story: release111-release-proof
complexity: complex
role: developer
stack: python
tier: substantial
call_budget: 120
defect_of: null
scope: "benchmark protocol/fixtures; live acceptance evidence; upgrade and public-snapshot checks; release docs"
scope_exclude: "Unrelated product features; automatic model downgrade; unapproved external publication; weakening quality gates"
relevant_files:
  - "scripts/usage_codex.py"
  - "scripts/usage_codex_report.py"
  - "scripts/call_mix.py"
  - "tests/test_usage_codex.py"
  - "tests/test_call_mix.py"
  - "docs/en/cost-telemetry.md"
  - "docs/ru/cost-telemetry.md"
  - "docs/en/model-providers.md"
  - "docs/ru/model-providers.md"
  - "docs/ru/research/release111-economy-results.md"
  - "changelog.d/codex-task-cost-111.md"
  - "tausik/tasks/r111-cross-host-economy-acceptance.md"
scope_paths:
  - "tests/test_release111_acceptance.py"
  - "docs/ru/research/release111-economy-results.md"
  - "docs/en/cost-telemetry.md"
  - "docs/ru/cost-telemetry.md"
  - "docs/en/model-providers.md"
  - "docs/ru/model-providers.md"
  - "tausik/"
  - "changelog.d/"
  - ".tausik/planning/release-111/"
  - "docs/en/"
  - "docs/ru/"
  - "scripts/usage_codex.py"
  - "scripts/usage_codex_report.py"
  - "scripts/call_mix.py"
  - "tests/test_usage_codex.py"
scope_tools: []
depends_on:
  - answer-rules-remeasured-after-three-sessions
  - cold-start-drill
  - public-snapshot-tests-read-excluded-files
  - r111-adaptive-model-routing
  - r111-budgeted-context-package
  - r111-compound-workflow-results
  - r111-glm-host-usage-adapter
  - r111-live-enforcement-capabilities
  - read-lever-chosen-and-measured
  - schema-migrations-of-the-release-run-as-one-campaign
  - test-suite-is-cut-to-what-guards-behaviour
completed_at: "2026-10-01T18:48:27Z"
resolution: null
resolution_reason: null
tracker_refs:
  - "github#199"
started_model_id: claude-opus-5
started_model_version: null
done_model_id: claude-opus-5
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
---

## Goal

Accept 1.11 using exact, naturally occurring Codex task usage and independent quality evidence. Do not consume the weekly quota on a synthetic benchmark campaign. Kilo/GLM remains theoretical under Decision #414.

## Acceptance Criteria

AC-1 Preserve the frozen baseline revision and independent six-case quality corpus; never reconstruct a convenient baseline after optimization. AC-2 Add exact native Codex task-window attribution from explicit task start/done events; report response rounds, input/cache/output/reasoning, failures/retries and unattributed usage. No timestamp guess or active-task guess. AC-3 Compare fixed host/model/reasoning/speed observations from useful pre/post work. Target at least 30% lower median Codex total tokens per accepted task with no quality regression; also report p90, complexity and response/read-call changes. If evidence is insufficient or target fails, say so and narrow/revert—do not change the baseline. AC-4 Decision #415: use at most one matched naturally occurring case per complexity after a bounded pilot; no synthetic paid repetitions merely to fill a table. Stop early on regression, identity drift or unreliable totals. AC-5 Release proof covers Codex capability/economy, upgrade/rollback, public snapshot and EN/RU docs. Decision #414: Kilo/GLM is theoretical and not a live quantitative prerequisite; Cursor/OpenRouter remain optional.

## Plan

[{"step": "Confirm frozen baseline/corpus and implement exact Codex task attribution without content persistence.", "done": true}, {"step": "Run a bounded naturally occurring Codex pilot, then at most one matched observed case per complexity while identity and quality remain fixed.", "done": true}, {"step": "Check upgrade/public snapshot and publish evidence, uncertainty and retained/reverted changes.", "done": true}]

## Rollback

Revert this task's isolated changes and retain baseline behavior; for data changes use tested backup/restore or reversible migration.

## Journal

- 2026-10-01T18:18:56Z [planning] — Decision #415 removes synthetic paid fan-out. Acceptance will reuse exact native Codex task windows from useful work; hard stop on unreliable totals, identity drift or quality regression. Decision #414 makes GLM theoretical.
- 2026-10-01T18:23:39Z [planning] — Exact Codex attribution design: response_item(custom_tool_call exec) is immediately followed by token_usage_record. Keep active slug only from explicit TAUSIK task start; include start/work/done response IDs; clear after done response. Require current DB status=done before accepted-task rollup. Incomplete/nested/foreign/fork windows stay unattributed. Persist no command, prompt or output.
- 2026-10-01T18:47:37Z [implementation] — Steps 1-2: exact native Codex task windows implemented with successful start/done result checks, failed-close rework, fork/nested/incomplete fail-closed handling, DB done admission, attempts/retries and model/reasoning/speed identity. Natural pilot found 16 exact completed tasks, but frozen six-case baseline remains unmeasured and no matched Astra/Sol/Terra cases exist. Decision #415 stops here: no synthetic paid run and no 30% claim.
- 2026-10-01T18:47:54Z [implementation] — Step 3: upgrade/rollback and public-snapshot proof passed in the 321-test focused lane (test_migrations, test_publication_snapshot, usage and docs). Codex support/doc parity lane passed separately. EN/RU telemetry and provider routing docs updated; RU acceptance report records HOLD/inconclusive, 97.6% cache share, 92% account quota snapshot, and the absence of matched Astra evidence.
- 2026-10-01T18:48:22Z [implementation] — AC-1: ✓ .tausik/planning/release-111/frozen-corpus.json SHA list remains the authority; baseline cells remain unmeasured. AC-2: ✓ tests/test_usage_codex.py::test_exact_task_window_includes_failed_close_rework_and_successful_close AC-3: ✓ docs/ru/research/release111-economy-results.md records inconclusive/HOLD; no 30% or Astra multiplier claim. AC-4: ✓ tests/test_usage_codex.py::test_inherited_fork_boundaries_do_not_open_a_child_task_window AC-5: ✓ tests/test_migrations.py and tests/test_publication_snapshot.py passed in the 321-test release-proof lane; EN/RU telemetry/provider docs updated. Negative: nested, inherited, failed-start, incomplete and non-done windows cannot become accepted task cost; unmatched baseline cannot become savings. Domain: live Codex journals produced 16 accepted task windows, 934 exact response rounds, identity and quota observations without storing transcript bodies. Root cause — measurement gap: the frozen pre-change task cells contain no exact task totals, so a matched percentage cannot be recovered after the fact; prevention is exact native boundaries for future natural pairs.
