---
slug: jsonl-pipeline-new-not-extending-usage-events-db
task: v14b-baseline-token-metrics
date: "2026-05-06"
edges: []
---

## Decision

JSONL pipeline (new) — not extending usage_events DB

## Rationale

AC #1 specifies .tausik/token_metrics.jsonl as the recording format. Existing usage_events table covers per-task cost attribution (different concern) and lacks cache_read/cache_create fields. Building a parallel JSONL pipeline keeps the new telemetry simple, append-only, and trivial to copy/share for cross-session benchmarking — no schema migration risk, no double-write coupling.
