---
slug: test-suite-is-cut-to-what-guards-behaviour
title: "The test suite is 12.5 thousand tests: cut it to what guards behaviour"
status: done
epic: release-111-economy-draft
story: release111-context-and-workflow
complexity: complex
role: developer
stack: python
tier: substantial
call_budget: 90
defect_of: null
scope: "Existing test-suite audit and consolidation; scoped verification selection; contributor testing guidance. No unrelated production features or blanket quality-gate disablement."
scope_exclude: null
relevant_files:
  - "tests/test_repo_coherence.py"
  - "tests/test_release_notes_1_9.py"
  - "tests/test_agent_quickstart.py"
  - "tests/test_crosscutting_registry.py"
  - "scripts/usage_observation.py"
  - "scripts/usage_codex.py"
  - "scripts/usage_codex_report.py"
  - "docs/en/testing-principles.md"
  - "docs/ru/testing-principles.md"
  - "docs/ru/codex-economy-baseline.md"
  - "docs/en/codex-economy-baseline.md"
  - "docs/_generated/doc-map.md"
  - "docs/ru/research/release-111-test-economy-2026-10-01.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths:
  - "tests/"
  - "scripts/gate_test_resolver.py"
  - "scripts/usage_observation.py"
  - "scripts/usage_codex.py"
  - "scripts/usage_codex_report.py"
  - "scripts/default_gates.py"
  - "scripts/gate_stack_dispatch.py"
  - "scripts/project_types.py"
  - "scripts/render_verify.py"
  - "bootstrap/bootstrap_config.py"
  - "docs/"
  - pyproject.toml
  - "tausik/"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - ".tausik/planning/release-111/"
scope_tools: []
depends_on:
  - "1-11-establish-a-codex-usage-baseline-that-can"
completed_at: "2026-10-01T15:55:05Z"
resolution: null
resolution_reason: null
tracker_refs:
  - "github#201"
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

Reduce the cost of developing TAUSIK 1.11 itself by retaining tests that detect meaningful failures and removing redundant or implementation-pinning checks. Historical inventory (12594 fast + 143 slow) is not a current measurement: refresh collection and timing. Deliver early scoped savings without waiting for compound workflow work; measure test execution, maintenance and model rerun/output costs separately.

## Acceptance Criteria

AC-1 Refresh collected test counts, full/scoped runtime, output volume and retries; distinguish test functions from parametrized cases. Classify by protected observable behavior/risk, duplicates, brittle implementation/prose pins, mock-only checks and generated freshness. Counts alone do not establish waste.
AC-2 Deliver an early bounded batch of high-confidence consolidation/removal after the native Codex baseline. No exhaustive manual per-test narrative or fixed percentage deletion target. A compact mapping per removed family names the surviving behavior tests, or explains why no required behavior was guarded. Parameterization improves maintainability but is not claimed to reduce executed cases by itself.
AC-3 Define task/iteration/release verification selection: relevant behavior and transitive consumers per change; broader integration checks when shared boundaries change; full maintained suite for release candidates and explicit impact triggers. Reuse evidence only with valid input/config fingerprints. Documentation-only/cosmetic changes require no invented behavior tests. Any relaxation of mandatory current gate behavior requires an explicit bounded exception or a tested policy change, not silent configuration weakening.
AC-4 Preserve failures for task gates, evidence integrity, hooks/security, migrations/restore, public snapshot and cross-host contracts. For consolidated critical families demonstrate known regression or targeted fault detection; NEGATIVE: missing evidence, invalid cache, unexpected affected consumers and partial execution cannot yield success. Reuse existing meaningful tests; do not add ceremonial tests to compensate for deletions.
AC-5 Report before/after executed and deselected counts, full/scoped time, output and model retries separately. No claim that fewer tests mechanically means fewer subscription tokens. Unrelated existing failures remain visible and attributed; no false green or hidden skip. Restore removed family if meaningful detection is lost.

## Plan

[{"step": "Refresh collection/runtime and rank expensive or brittle test families; identify the smallest useful early batch.", "done": true}, {"step": "Remove or consolidate low-value families using compact retained-behavior evidence; define risk-based verification selection and explicit exception boundaries.", "done": true}, {"step": "Validate critical failure detection, scoped consumers and release checks; report before/after costs including retries and maintenance, without quota claims.", "done": true}]

## Rollback

Revert only this task's changes; preserve pre-change behavior and historical evidence. For migrations verify database backup restoration.

## Journal

- 2026-10-01T15:39:38Z [implementation] — Baseline default lane: 12622 passed, 34 skipped, 143 deselected, 9 failed in 215.87s. Failures expose missing RU protocol, untracked-source selector discovery, mypy annotations and positional local-cache INSERT in new telemetry; five unrelated broad-except lint findings also present. Preserve these checks and fix findings; do not remove red tests. Coherence tests repeatedly scan mutable live repo/DB; replace with real collectors on planted small repositories.
- 2026-10-01T15:50:27Z [implementation] — Default-lane before/after: 215.87s -> 125.26s (~42% faster), 12665 -> 12657 executed/selected cases; 143 slow cases excluded both times. Initial 9 failures reduced to formatting-only failure in four annotated files; fixing formatting and scoped verification. Coherence retained 13 meaningful tests at 1.84s; disabling its duplicate detector produces expected failure. Source selectors retain affected doc/command consumers. This measures test time, NOT model token savings.
- 2026-10-01T15:52:34Z [implementation] — AC-1: ✓ refreshed function/case inventory and before/after logs recorded. AC-2: ✓ 6 editorial functions + redundant smoke removed with family mapping in docs/ru/research/release-111-test-economy-2026-10-01.md; meaningful checks retained. AC-3: ✓ EN/RU testing principles define scoped iteration and full release checks; narrowed doc selectors validated against affected/unrelated pages and command source. AC-4: ✓ planted-fault real collectors pass; detector mutation fails as expected; frozen 6-case acceptance SHA256 files unchanged. Initial red checks fixed, not removed. AC-5: ✓ default lane 215.87 -> 125.26 seconds, 143 deselected both; tokens/retries unknown, no quota claim. Formatting-only residual fixed: 6 passed. Domain: fixture contains real defects and actual collectors, no reliance on dirty working DB.
- 2026-10-01T15:54:13Z [implementation] — NO-DEAD-END / root cause: #3237 exposed different Ruff versions: pytest used venv 0.15.12 while gate used PATH 0.16.5. ci-constraints.txt already pins 0.16.5. Aligned venv to existing pin and reverted all five added suppressions; those source files have no semantic diff. Test-time before/after pair used the same old environment; no timing claim from dependency upgrade.
- 2026-10-01T15:55:04Z [implementation] — AC-4: ✓ tests/test_repo_coherence.py exercises real planted-fault detection and error reporting; tests/test_usage_observation.py and tests/test_usage_codex.py preserve telemetry negatives. AC-3: ✓ tests/test_crosscutting_registry.py checks source discovery including unstaged/ignored files. Green verification_run #3238 covers this task. NO-DEAD-END: closure parser required explicit test-path evidence; added without rerunning green tests.
