---
slug: r111-natural-cost-validation
title: "1.11: validate accepted-task cost on natural work"
status: done
epic: release-111-economy-draft
story: release111-release-proof
complexity: medium
role: developer
stack: python
tier: light
call_budget: 20
defect_of: null
scope: "Existing economy report, retained usage records and acceptance protocol; no new telemetry platform."
scope_exclude: "Paid synthetic benchmarks, external publication, broad refactoring and weakened gates."
relevant_files:
  - "docs/ru/research/release111-economy-results.md"
scope_paths:
  - ".tausik/planning/release-111"
  - "docs/ru/research/release111-economy-results.md"
scope_tools: []
depends_on: []
completed_at: "2026-10-01T20:01:00Z"
resolution: null
resolution_reason: null
tracker_refs: []
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

Assess release economy from naturally occurring comparable tasks without recreating the missing historical baseline or attributing account-wide quota to TAUSIK.

## Acceptance Criteria

AC-1 Freeze comparison eligibility, model/reasoning/speed and quality criteria before collecting new work. AC-2 Reuse only natural eligible tasks under Decision #415; include retries, coordinator overhead and unassigned costs separately. AC-3 Report measured cost/usage and quality with sample size; incompatible or absent baselines stay inconclusive, never a savings percentage. AC-4 Deliver an explicit release readiness verdict including the live enforcement blocker.

## Plan

[{"step": "Freeze eligible natural-work comparisons and quality criteria", "done": true}, {"step": "Collect only naturally occurring comparable tasks and separate unattributed overhead", "done": true}, {"step": "Publish measured or inconclusive readiness verdict without synthetic benchmarks", "done": true}]

## Rollback

Revert this task's bounded changes; preserve raw measurements and prior inconclusive verdict.

## Journal

- 2026-10-01T20:00:02Z [implementation] — Step1 freeze reused pre-existing corpus at revision72862321: S1/S2/M1/M2/C1/C2 all unmeasured. Eligible pair requires exact native task boundaries,done state,same case/complexity/model/reasoning/standard speed,unchanged quality hashes,and all attempts/rework. No synthetic replay. Missing mapping or baseline stays inconclusive.
- 2026-10-01T20:00:03Z [implementation] — Step2 natural snapshot:2604 project responses;337699140 input incl329602048 cached;1115285 output;329818 reasoning.18 accepted task windows,1036 accepted responses,134371615 total tokens,34 attempts/16 retries.1557 unattributed task responses and1568 excluded rows separate.17 single-identity tasks;1 mixed excluded. No frozen case has a measured baseline or valid comparable pair.
- 2026-10-01T20:00:55Z [implementation] — Step3 Domain: native snapshot and frozen corpus support the published HOLD decision. Negative: zero matched pairs remains inconclusive, never 0% or a saving. Verify3296 green for documentation scope;ruff/pytest not applicable and skipped.
- 2026-10-01T20:00:56Z [implementation] — AC verified: 1. ✓ Pre-existing frozen corpus revision 72862321 defines six unmeasured cells, fixed identity and frozen quality checks before natural collection. 2. ✓ Native natural snapshot includes 18 accepted windows, 1036 responses, 34 attempts/16 retries; 1557 unattributed responses and 1568 excluded rows remain separate. 3. ✓ Comparable pair n=0, so target remains inconclusive with no savings percentage; descriptive model medians are explicitly non-causal. 4. ✓ Release verdict HOLD; Codex live blocker resolved for bounded routes, GLM theoretical per Decision #414. Scoped verify #3296 passed.
