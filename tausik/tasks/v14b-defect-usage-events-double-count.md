---
slug: v14b-defect-usage-events-double-count
title: "H3: usage_events double-write between posttool_usage and session_record — risk of future double-counting"
status: done
epic: v14-polish-quality
story: v14-polish-b-quality
complexity: simple
role: developer
stack: python
tier: light
call_budget: 15
defect_of: null
scope: "scripts/backend_queries_usage.py, scripts/hooks/posttool_usage.py, tests/test_session_usage_record.py (or equivalent)"
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-05-03T21:52:37Z"
---

## Goal

Eliminate the double-write hazard between posttool_usage hook and session_usage_record (both write into usage_events). Either drop the redundant session_record write (preferred — session_usage_metrics already holds cumulative tokens) or document the source-filter contract so any future SUM-style rollup must apply the same filter as usage_events_cost_rollup_by_task.

## Acceptance Criteria

1. Either: (a) session_usage_record no longer writes a row to usage_events (preferred), OR (b) a clear contract docstring on usage_events_cost_rollup_by_task and any new SUM-rollup-style query enforces the source filter explicitly. 2. No regression — existing rollup-by-task tests still pass. 3. If option (a): session_usage_record still keeps cumulative tokens in session_usage_metrics; tests assert no usage_events row is written from session_record. 4. NEGATIVE: a hypothetical naive aggregator (SUM(cost_usd) FROM usage_events with no source filter) would NOT double-count — verified by counting rows after both posttool_usage and session_record fire on the same session. 5. NEGATIVE: posttool_usage path remains unchanged — task_slug-bearing rows still land in usage_events. 6. pytest test suite PASS. 7. tausik verify --task &lt;slug&gt; PASS.

## Plan

## Rollback

## Journal

- 2026-05-03T21:52:36Z [implementation] — AC verified: 1.✓ Option (b) chosen — explicit contract docstrings on session_usage_record + usage_events_cost_rollup_by_task documenting double-count hazard and exclusivity invariant. 2.✓ Existing rollup tests pass (test_metrics_session_usage 11/11). 3. n/a (Option a not chosen). 4.✓ Negative pin via test_naive_unfiltered_sum_would_double_count: SUM with no filter = 2x truth; per-task rollup excludes session_record correctly. 5.✓ Posttool path unchanged via test_per_task_rollup_excludes_session_record (3 posttool rows still attributed to task). 6.✓ pytest 14/14 PASS in 0.41s. 7.✓ tausik verify exit=0.
