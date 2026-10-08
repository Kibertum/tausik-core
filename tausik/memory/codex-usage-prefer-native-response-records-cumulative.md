---
slug: codex-usage-prefer-native-response-records-cumulative
title: "Codex usage: prefer native response records; cumulative counters are fallback, not extra cost"
type: pattern
tags:
  - codex
  - economy
  - usage
task: "1-11-establish-a-codex-usage-baseline-that-can"
edges: []
---

Native token_usage_record.usage and event_msg token_count.info.total_token_usage coexist. Adding both double-counts usage. Incremental parser in scripts/usage_codex.py deduplicates response IDs, keeps cumulative-only threads separate and leaves task attribution unknown without explicit linkage. Live independent reconciliation: 119 project responses matched. Quota timestamps are account-wide, not task cost.
