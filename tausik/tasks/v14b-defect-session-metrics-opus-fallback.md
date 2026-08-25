---
slug: v14b-defect-session-metrics-opus-fallback
title: "H2: session_metrics.parse_transcript falls back to \"opus\" pricing on missing model — Sonnet/Haiku transcripts mis-attributed"
status: done
epic: v14-polish-quality
story: v14-polish-b-quality
complexity: simple
role: developer
stack: python
tier: trivial
call_budget: 10
defect_of: null
scope: "scripts/hooks/session_metrics.py, tests/test_session_metrics_hook.py"
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-03T21:50:13Z"
---

## Goal

Drop the silent `model or "opus"` fallback in session_metrics.parse_transcript. When the transcript has no model field, return cost_usd=0.0 and emit a stderr warning (parity with posttool_usage). No more silent 5×/19× over-attribution of Sonnet/Haiku transcripts at Opus rates.

## Acceptance Criteria

1. parse_transcript no longer falls back to "opus" rates when the transcript has no model field. 2. On missing model: cost_usd is 0.0 and a stderr warning is emitted (mirrors posttool_usage behavior). 3. NEGATIVE: empty model string ("") also returns cost_usd=0.0, not Opus rates. 4. NEGATIVE: missing transcript file path returns the existing zero-cost result without raising. 5. tests/test_session_metrics_hook.py covers the missing-model path explicitly. 6. pytest tests/test_session_metrics.py PASS (or test_session_metrics_hook.py — whichever exists). 7. tausik verify --task &lt;slug&gt; PASS.

## Plan

## Rollback

## Journal

- 2026-05-03T21:50:13Z [implementation] — AC verified: 1.✓ 'or opus' fallback dropped — session_metrics.py:81 now branches on model truthiness via test_missing_model_returns_zero_cost_not_opus_rates. 2.✓ stderr warning emitted via test_cli_no_model_emits_stderr_warning ('missing model' string). 3.✓ Empty string model → 0.0 via test_empty_model_string_returns_zero_cost. 4.✓ Nonexistent path handled via test_invalid_path_raises_or_handled. 5.✓ TestParseTranscriptModelHandling + TestParseTranscriptViaCLI added (7 cases). 6.✓ pytest 7/7 PASS in 0.15s. 7.✓ Sonnet rates preserved via test_sonnet_transcript_no_longer_attributed_to_opus ($3 not $15). 8.✓ tausik verify exit=0.
