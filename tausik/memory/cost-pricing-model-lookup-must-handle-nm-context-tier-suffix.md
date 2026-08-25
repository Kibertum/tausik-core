---
slug: cost-pricing-model-lookup-must-handle-nm-context-tier-suffix
title: "cost_pricing model lookup must handle [Nm] context-tier suffix"
type: gotcha
tags:
  - "1m-context"
  - cost-telemetry
  - model-id
  - v1.4-polish
task: v14b-defect-cost-pricing-1m-suffix
edges: []
---

1M-context Claude models carry a `[1m]` suffix in their canonical ID (e.g. `claude-opus-4-7[1m]`). A bare `dict.get(model_id)` lookup in cost_pricing returned None for every 1M-context tool call, so posttool_usage wrote `cost_usd=0.0` for the entire session and B4 cost telemetry silently degraded.

Fix: explicit `[1m]` rows in `_MODEL_PRICING` (2× base — Anthropic-documented Sonnet 1M premium, applied to other tiers pending separate published rates) AND a strip-suffix fallback (`re.sub(r"\[[^\]]+\]\s*$", "", key)`) so unknown bracket variants gracefully fall back to the base canonical ID.

Pattern applies to any future suffix variants (e.g. `[batch]`, `[2m]`).
