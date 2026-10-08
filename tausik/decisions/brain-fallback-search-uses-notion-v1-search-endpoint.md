---
slug: brain-fallback-search-uses-notion-v1-search-endpoint
task: brain-mcp-tools-read
date: "2026-04-23"
edges: []
---

## Decision

Brain fallback search uses Notion /v1/search endpoint filtered by parent.database_id ∈ brain db_ids, not per-database databases.query calls.

## Rationale

One HTTP call vs 4. /v1/search matches page titles (body search is not available via API anyway). Dash-normalization of page ids between config and Notion response lets both formats work. Returned pages are normalized through the same brain_sync.map_page_to_row path as local rows, so format_record stays uniform.
