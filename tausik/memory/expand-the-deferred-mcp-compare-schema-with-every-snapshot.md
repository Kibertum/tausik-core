---
slug: expand-the-deferred-mcp-compare-schema-with-every-snapshot
title: "Expand the deferred MCP compare schema with every snapshot option"
type: dead_end
tags: []
task: constrain-mcp-benchmark-snapshot-writes-to
edges: []
---

Approach: Expand the deferred MCP compare schema with every snapshot option
Reason: The added serialized schema exceeded the MCP surface ratchet; handler-boundary validation fixes the write vulnerability without charging every non-deferred turn for the schema.
