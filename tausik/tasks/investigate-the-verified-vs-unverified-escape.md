---
slug: investigate-the-verified-vs-unverified-escape
title: "Investigate the verified-vs-unverified escape paradox and risk-backtest AUC"
status: done
epic: release-1-11-3
story: release1113-hygiene-calibration
complexity: null
role: qa
stack: python
tier: null
call_budget: null
defect_of: null
scope: "scripts/backend_defect_escape.py (stratified verified-vs-unverified cut by complexity), scripts/render_metrics.py (render the stratified rows), tests/test_defect_escape.py"
scope_exclude: "verify policy logic, risk_compute, gate_runner"
relevant_files:
  - "scripts/backend_defect_escape.py"
  - "scripts/render_metrics.py"
  - "tests/test_defect_escape.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths: []
scope_tools: []
assurance_profiles: []
assurance_impact: null
depends_on: []
completed_at: "2026-10-06T22:14:57Z"
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

Explain why verified tasks escape defects more often than unverified ones (9.8% vs 1.5%) and whether the risk score discriminates at all (AUC 0.5364 = coin flip); land a fix or a recorded decision

## Acceptance Criteria

Written diagnosis with numbers from the tasks table (sample sizes, windows); either a fix (recalibrated risk score or changed verify policy) or a documented decision to keep as-is. Negative scenario: if the paradox is a small-sample artifact the conclusion names the sizes and the statistical test used, not a hand-wave.

## Plan

## Rollback

git revert of the commit carrying this change

## Journal

- 2026-10-06T22:12:44Z [implementation] — DIAGNOSIS (read-only analysis via project SQLiteBackend; window: done n=1795 non-defect, completed 2026-03-14..2026-10-06; #126 baseline 2026-07-20 was 5.1%/1.3% at n=625/380). NUMBERS: aggregate verified 9.9% (138/1400) vs unverified 1.5% (6/395), Fisher exact two-sided p=8.83e-10 — the gap is NOT a small-sample artifact and the conclusion names it. STRATIFIED (now in metrics): complex 18.1% (30/166) vs 0.0% (0/43) p=9.77e-04; medium 12.4% (82/660) vs 1.1% (2/178) p=3.57e-07; simple 5.8% (22/380) vs 2.4% (4/166) p=0.124 (NS); unknown 2.1% (4/194) vs 0.0% (0/8) p=1.0 — the gap survives complexity held fixed, so selection-on-complexity alone does not explain it (Simpson hypothesis of #267 falsified as the sole cause). CAUSE 1 — LEFT-CENSORING: defect_of filing practice starts 2026-04 (filings by month: 04:27, 05:7, 06:15, 07:58, 08:28, 09:49, 10:16); ZERO defects point at pre-April closures; 230 of 395 unverified closures are March work (real dev work: db-indexes, fts5-triggers, schema-migrations, rag-path-traversal — not docs) that structurally cannot appear as escaped. CAUSE 2 — DEAD TREATMENT: since QG-2 Verify-First (July) verification is mandatory; unverified closures since July: 15 (Jul 2, Sep 12, Oct 1) vs 856 verified; the arms compare different eras. ERA-CLEAN CUT: unverified after 2026-04-15: 6/98 = 6.1% vs verified July+ 117/856 = 13.7% — a remaining gap on a vanishing population with no policy lever. The 6 unverified escapes listed: notification-hooks, brain-mcp-server-wiring, brain-decide-auto-route, brain-bypass-marker-hardening, brain-config-mirror-path-contract (all April), full-suite-runs-only-in-ci-and-ci-has-not-run (Sep, qa). RISK BACKTEST: AUC 0.5377 aggregate, 0.5411 verified-only (escaped n=131 vs clean n=874), complexity alone 0.5977 — risk_score has no discriminative power in either arm. OUTCOME: fix = stratified cut by_complexity_and_verification shipped in defect_escape_metrics + render (tests/test_defect_escape.py::TestStratifiedVerification, 10 passed); decision #424 = keep verify policy, never route on risk_score; aggregate line read only beside its strata. AC NEGATIVE satisfied: sizes and the statistical test (Fisher exact, two-sided) are named for every comparison.
- 2026-10-06T22:14:44Z [implementation] — AC verified: 1. [written diagnosis with numbers: sample sizes, windows] OK — journal carries the full diagnosis (aggregate 138/1400 vs 6/395 Fisher p=8.83e-10; per-stratum sizes and p-values; window 2026-03-14..2026-10-06, done n=1795; #126 baseline named; causes: left-censoring from 2026-04 filing practice, dead treatment since July QG-2). 2. [fix or documented decision] BOTH — fix: by_complexity_and_verification shipped in defect_escape_metrics + render_metrics (live output inspected); decision #424 recorded via tausik decide with rejected alternatives. NEGATIVE [small-sample artifact must name sizes and test] OK — every comparison names its sizes and Fisher exact two-sided p; the aggregate is explicitly NOT an artifact (p=8.8e-10). Verify run #3558 exit=0, handle presented. Red run #3557 was test_dedupe catching my aggregate test duplicating test_by_verification's shape — merged into the stratified test (both projections of the same rows), baseline back to 282/669; not a dead end, standard dedupe resolution.
- 2026-10-06T22:14:56Z [implementation] — NO-DEAD-END: red verify run #3557 was the test_dedupe gate working as designed — my new aggregate test duplicated the existing test_by_verification shape (group 119). Merged its assertions into the stratified test; audit back to baseline 282/669; green re-verify #3558.
- 2026-10-06T22:15:05Z [done] — AC-1 (written diagnosis with numbers, sizes, windows; fix or documented decision; negative scenario): ✓ journal diagnosis above (sizes + Fisher exact p for every comparison, window 2026-03-14..2026-10-06, n=1795); ✓ tests/test_defect_escape.py::TestStratifiedVerification::test_equal_within_strata_but_aggregate_reads_verified_worse (the shipped stratified cut); ✓ tests/test_defect_escape.py::TestStratifiedVerification::test_render_prints_the_stratified_arms; ✓ live manual run ausik metrics (stratified lines in Defect Escape section); ✓ green verification_run #3558 (exit=0); ✓ decision #424 (keep verify policy; risk_score never routes). Domain: the diagnosis is valid outside tests — real corpus numbers, era split, and filing-practice origin read from the live tasks table, and the metric renders on the production DB.
