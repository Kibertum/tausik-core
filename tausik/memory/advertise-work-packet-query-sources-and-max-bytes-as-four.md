---
slug: advertise-work-packet-query-sources-and-max-bytes-as-four
title: "Advertise work-packet query, sources and max_bytes as four separate MCP task-show properties"
type: dead_end
tags:
  - mcp
  - prefix
  - verification
task: r111-bounded-work-packet
edges: []
---

Approach: Advertise work-packet query, sources and max_bytes as four separate MCP task-show properties
Reason: Scoped pytest caught the MCP serialized-surface ratchet: schema grew 454 bytes above baseline. Replace the verbose property set with one compact JSON-string packet argument and trim existing task-tool descriptions enough to keep the total surface at or below baseline; do not raise the ratchet for an economy feature.
