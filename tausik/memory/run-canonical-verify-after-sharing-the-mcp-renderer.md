---
slug: run-canonical-verify-after-sharing-the-mcp-renderer
title: "Run canonical verify after sharing the MCP renderer"
type: dead_end
tags: []
task: add-cli-version-flag-and-block-session-start-on-a
edges: []
---

Approach: Run canonical verify after sharing the MCP renderer
Reason: A legacy host-binding test mocked the old best-effort _run_tausik helper, while the hook now must inspect the CLI exit code and stderr to surface a release refusal. Update the test at the subprocess boundary and assert both invocation and no blocker on success.
