---
slug: notion-pages-create-response-has-plain-text-outgoing
title: "Notion pages.create response has plain_text; outgoing payload only has text.content"
type: gotcha
tags:
  - api
  - brain
  - notion
  - testing
task: brain-mcp-tools-write
edges: []
---

When you send POST /v1/pages with properties like `{"Name": {"title": [{"text": {"content": "X"}}]}}`, Notion responds with the same page re-shaped: each rich_text/title item gains a `plain_text` field. brain_sync._concat_text reads `plain_text` (not `text.content`), so any fake client used in write-path tests MUST enrich outgoing payloads with plain_text before echoing them back — otherwise map_page_to_row returns empty names/fields and upsert stores blanks. See tests/test_brain_mcp_write.py._enrich_plain_text for the canonical shape.
