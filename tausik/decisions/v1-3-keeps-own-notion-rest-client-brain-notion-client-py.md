---
slug: v1-3-keeps-own-notion-rest-client-brain-notion-client-py
task: null
date: "2026-04-28"
edges: []
---

## Decision

v1.3 keeps own Notion REST client (`brain_notion_client.py`); migration to Notion's official MCP deferred to v1.4 hybrid mode

## Rationale

User decision after discovering Notion released official MCP. Our impl has unique value (offline mirror, FTS5, privacy scrubbing, project hashing, classifier, WebFetch hooks) ~30-40% of brain code is duplicate (REST client, sync, basic search-surface). Refactor too risky for v1.3. v1.4 should add hybrid: detect Notion MCP in .mcp.json, use as transport; fallback to own client. Keep privacy/mirror/classifier/hooks layers in both modes.
