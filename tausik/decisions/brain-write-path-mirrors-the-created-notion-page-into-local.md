---
slug: brain-write-path-mirrors-the-created-notion-page-into-local
task: brain-mcp-tools-write
date: "2026-04-23"
edges: []
---

## Decision

Brain write-path mirrors the created Notion page into local SQLite synchronously via map_page_to_row + upsert_page, instead of setting a dirty flag that the next sync would clear.

## Rationale

Instant read consistency — a brain_store_* call can be followed by brain_search and see the new row immediately. Sync primitives already map Notion → SQLite; reusing them costs no new code. Failure during upsert returns status=ok_not_mirrored without crashing the write. Alternative (dirty flag + async reconcile) would need extra state + background sync trigger in MCP, not worth the complexity for v1.
