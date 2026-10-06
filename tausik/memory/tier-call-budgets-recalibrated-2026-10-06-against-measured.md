---
slug: tier-call-budgets-recalibrated-2026-10-06-against-measured
title: "Tier call budgets recalibrated 2026-10-06 against measured percentiles"
type: context
tags:
  - "tier,calibration,budget,metrics"
task: recalibrate-tier-call-budgets-against-observed
edges: []
---

Tier thresholds moved 10/25/60/150/400 -> 24/33/66/113/200 (task recalibrate-tier-call-budgets-against-observed): each new bound is the p90 of that tier's measured call_actual over done tasks, clamped to [p50, 3xp50]. The ratchet is budget_calibration_check in scripts/backend_tier_metrics.py — it re-compares bounds vs rolling p50 actuals on every 	ausik metrics (starved = bound below p50, hard fail; decorated = beyond BUDGET_CALIBRATION_FACTOR=3.0x; n<5 tiers report unmeasured and never set the verdict). When actuals drift, recalibrate from a fresh 	ausik metrics p50/p90 reading instead of hand-picking numbers. Verify run #3555 exit=0.
