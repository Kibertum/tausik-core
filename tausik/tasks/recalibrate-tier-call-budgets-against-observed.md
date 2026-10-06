---
slug: recalibrate-tier-call-budgets-against-observed
title: "Recalibrate tier call budgets against observed actuals"
status: done
epic: release-1-11-3
story: release1113-hygiene-calibration
complexity: medium
role: architect
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/backend_tier_metrics.py"
  - "scripts/backend_crud.py"
  - "scripts/backend_queries_metrics.py"
  - "scripts/render_metrics.py"
  - "tests/test_metrics_tier.py"
  - "tests/test_agent_units.py"
  - "tests/test_agent_units_cli.py"
  - "tests/test_med_findings_fix.py"
  - "tests/test_task_update_writes_all_or_nothing.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths: []
scope_tools: []
assurance_profiles: []
assurance_impact: null
depends_on: []
completed_at: "2026-10-06T22:01:21Z"
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

Make tier call budgets match measured actuals so budgets constrain work instead of decorating it (substantial budget 105.1 vs actual 53.3; median actual/budget 0.04)

## Acceptance Criteria

New budgets derived from measured percentiles per tier with the derivation shown; a check keeps budgets within a stated factor of rolling actuals. Negative scenario: budgets must not drop below p50 actuals — a budget that blocks legitimate work fails the check.

## Plan

## Rollback

## Journal

- 2026-10-06T21:55:52Z [implementation] — Finished the remaining items: (1) fixed duplicated `if upper < p50:` line in budget_calibration_check (working-tree syntax breakage); (2) added guard — all-unmeasured corpus returns None instead of printing an unearned "ok"; (3) parametrized tests in test_metrics_tier.py (verdict boundaries via fake q: starved at upper<p50, ok at upper==p50/2x/exactly 3x, decorated beyond; starved beats decorated for status; no-actuals and n<5 corpuses return None) + render smoke "Budget calibration: ok"; (4) fixed two seeds still on the old ladder (test_agent_units.py test_sets_actual_without_changing_tier and test_agent_units_cli.py test_budget_only_derives_tier: budget 30→40, 33<40<=66 = moderate); (5) pytest 4 files green — 80 passed; (6) bootstrap redeploy done; (7) live check on this repo: "Budget calibration: ok (factor 3.0x)", trivial/light/moderate/substantial ok, deep unmeasured; (8) [Unreleased] entries added to CHANGELOG.md + CHANGELOG.ru.md.
- 2026-10-06T22:01:09Z [implementation] — AC verified: 1. [budgets from measured percentiles, derivation shown] OK — _TIER_THRESHOLDS 24/33/66/113/200, each = p90 of measured call_actual clamped to [p50, 3xp50]; derivation comment in backend_crud.py lines 20-36 (trivial p50 8.0/p90 24.1 n=50 -> 24; light 11/35 n=209 -> 33; moderate 22/68 n=377 -> 66; substantial 38/112.8 n=149 -> 113; deep n=1 unmeasured -> held 200 < old 400 for monotonicity). 2. [check keeps budgets within stated factor of rolling actuals] OK — budget_calibration_check with BUDGET_CALIBRATION_FACTOR=3.0 in backend_tier_metrics.py, wired into get_metrics (backend_queries_metrics.py) and rendered as the 'Budget calibration' section; live run on this repo: 'Budget calibration: ok (factor 3.0x)', trivial/light/moderate/substantial all ok, deep unmeasured; verify run #3555 exit=0. NEGATIVE [budgets must not drop below p50 actuals] OK — starved verdict (upper < p50) is the hard fail and wins the status; parametrized tests in test_metrics_tier.py cover upper<p50=starved, upper==p50=ok, beyond 3x=decorated, starved-beats-decorated, all-unmeasured->None; every measured tier sits above its p50 live (24>8, 33>11, 66>22, 113>38).
- 2026-10-06T22:01:20Z [implementation] — NO-DEAD-END: red verify run #3554 was the scoped run doing its job — it caught tests/test_task_update_writes_all_or_nothing.py::test_the_mixed_call_still_works_when_nothing_is_refused still seeded on the old ladder (call_budget=12 -> light under 10/25/60, trivial under 24/33/66). Fixed by raising the seed to 26 (24 < 26 <= 33 -> light, intent preserved); re-verify #3555 exit=0.
