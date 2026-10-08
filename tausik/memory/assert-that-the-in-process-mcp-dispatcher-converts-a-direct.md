---
slug: assert-that-the-in-process-mcp-dispatcher-converts-a-direct
title: "Assert that the in-process MCP dispatcher converts a direct session-start refusal into a response st"
type: dead_end
tags: []
task: add-cli-version-flag-and-block-session-start-on-a
edges: []
---

Approach: Assert that the in-process MCP dispatcher converts a direct session-start refusal into a response string
Reason: The dispatcher intentionally propagates ServiceError to the MCP server boundary; the behavioral contract is the raised refusal before any session row, so the focused test must assert that exception and its version details.
