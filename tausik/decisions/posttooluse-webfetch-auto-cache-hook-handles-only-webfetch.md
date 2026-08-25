---
slug: posttooluse-webfetch-auto-cache-hook-handles-only-webfetch
task: brain-webfetch-hook
date: "2026-04-24"
edges: []
---

## Decision

PostToolUse WebFetch auto-cache hook handles only WebFetch, not WebSearch

## Rationale

WebSearch's tool_response is a single markdown blob covering multiple result URLs — there's no canonical URL to key a web_cache entry on, and writing the blob under any one result's URL would be lossy and misleading for the read-side (exact-URL lookup would fetch a multi-page summary, not the intended page). FTS5 on content written by WebFetch already services WebSearch queries via the PreToolUse hook, so the value of caching WebSearch separately is near zero. If we ever need query-level caching, do it under a synthetic `websearch://{query_hash}` URL — but that's a separate task.
