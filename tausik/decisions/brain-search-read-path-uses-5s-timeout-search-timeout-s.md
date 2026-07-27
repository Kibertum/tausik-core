---
slug: brain-search-read-path-uses-5s-timeout-search-timeout-s
task: brain-search-timeout-5s
date: "2026-05-06"
edges: []
---

## Decision

brain_search read-path uses 5s timeout (SEARCH_TIMEOUT_S); writes keep 10s (DEFAULT_TIMEOUT). Per-call timeout kwarg in NotionClient._request lets caller override.

## Rationale

/start Phase 1.5 cannot block on Notion — dashboard render is critical path. Read-fallback is best-effort and 5s is more than enough on healthy network. Writes are wizards (brain init / store_decision) where a slightly longer round-trip is acceptable. Asymmetric timeout matches asymmetric criticality.
