---
slug: for-1m-context-model-pricing-apply-2-base-tier-multiplier
task: v14b-defect-cost-pricing-1m-suffix
date: "2026-05-03"
edges: []
---

## Decision

For 1M-context model pricing, apply 2× base-tier multiplier across all canonical IDs ([1m] variants) instead of waiting for separately published Anthropic rates per model.

## Rationale

Anthropic publicly documents the 2× premium for Sonnet 1M only. Opus and Haiku 1M-context pricing isn't separately published as of v1.4. We needed cost_usd > 0.0 for current Opus 1M sessions immediately (the bug was every event recording 0.0). 2× across the board produces a defensible estimate that's close-enough for ROI tracking, with a strip-suffix fallback so unknown variants degrade to the 200k tier instead of crashing. Documented in cost_pricing.py's module docstring; revisit when Anthropic publishes per-model 1M rates.
