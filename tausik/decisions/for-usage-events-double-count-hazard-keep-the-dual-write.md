---
slug: for-usage-events-double-count-hazard-keep-the-dual-write
task: v14b-defect-usage-events-double-count
date: "2026-05-03"
edges: []
---

## Decision

For usage_events double-count hazard: keep the dual-write (posttool + session_record) and document the exclusivity contract via docstring + regression test, instead of dropping the redundant session_record write.

## Rationale

Existing test_metrics_session_usage::test_metrics_record_session_persists_usage explicitly asserts session_record events ARE written, and the schema CHECK constraint enumerates 'session_record' as a legitimate source. Removing the dual-write would break the documented contract used by external rollup queries that expect a unified event stream. The actual hazard (a future SUM aggregator that double-counts) is addressable via documentation + a regression test that pins the 2× pattern numerically — that surfaces if anyone introduces a naive aggregator without the source filter. Lower-risk than schema/contract change.
