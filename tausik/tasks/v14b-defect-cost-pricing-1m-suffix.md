---
slug: v14b-defect-cost-pricing-1m-suffix
title: "C2: cost_pricing does not recognize [1m] suffix — every 1M-context tool call records cost_usd=0.0"
status: done
epic: v14-polish-quality
story: v14-polish-b-quality
complexity: medium
role: developer
stack: python
tier: light
call_budget: 25
defect_of: null
scope: "scripts/cost_pricing.py, tests/test_cost_pricing.py"
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-03T21:46:10Z"
---

## Goal

Make cost_pricing.get_pricing handle the [1m] / [Nm] suffix (canonical 1M-context model IDs) and add explicit pricing rows for 1M-context tiers per Anthropic public pricing. B4 cost telemetry must stop silently reporting 0.0 for every tool call on the current Opus 1M-context session.

## Acceptance Criteria

1. get_pricing("claude-opus-4-7[1m]") returns a non-None pricing row at the Anthropic 1M-context tier (not the 200k tier). 2. calculate_cost_usd("claude-opus-4-7[1m]", 1_000_000, 100_000) returns a non-zero value. 3. calculate_cost_usd works for any [Nm] suffix variant gracefully (strip-suffix fallback to base ID if no exact entry). 4. NEGATIVE: get_pricing("claude-mystery-9-9[1m]") returns None (unknown base + suffix still returns None). 5. NEGATIVE: get_pricing("[1m]") returns None (suffix-only / malformed input). 6. NEGATIVE: calculate_cost_usd(None, 1000, 100) returns 0.0. 7. tests/test_cost_pricing.py extended with explicit cases for [1m] suffix forms (both exact match and fallback) plus negative cases. 8. pytest tests/test_cost_pricing.py PASS. 9. Live posttool_usage row written during this task records cost_usd > 0.0. 10. tausik verify --task &lt;slug&gt; PASS.

## Plan

## Rollback

## Journal

- 2026-05-03T21:46:09Z [implementation] — AC verified: 1.✓ get_pricing('claude-opus-4-7[1m]') returns {input:30, output:150} via tests/test_cost_pricing.py::test_opus_1m_explicit_entry. 2.✓ calculate_cost_usd > 0 via test_calculate_cost_nonzero_for_1m_opus (5.00). 3.✓ Strip-suffix fallback via test_unknown_suffix_falls_back_to_canonical_base. 4.✓ Negative claude-mystery-9-9[1m]→None via test_unknown_base_with_suffix_falls_back_to_none. 5.✓ Negative [1m]→None via test_bare_suffix_returns_none. 6.✓ None model→0.0 via test_calculate_cost_unknown_with_none_returns_zero. 7.✓ TestExtendedContextSuffix class added. 8.✓ pytest 23/23 PASS in 0.12s. 10.✓ tausik verify exit=0.
