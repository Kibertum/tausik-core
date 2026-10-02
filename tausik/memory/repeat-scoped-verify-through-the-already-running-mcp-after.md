---
slug: repeat-scoped-verify-through-the-already-running-mcp-after
title: "Repeat scoped verify through the already-running MCP after redeploy"
type: dead_end
tags:
  - mcp-drift
  - verification
task: r111-bounded-work-packet
edges: []
---

Approach: Repeat scoped verify through the already-running MCP after redeploy
Reason: All source static gates passed, but running-source drift correctly refused because the MCP process imported five changed files before this task. Per the gate remediation and MCP-first policy, switch only this verify/close path to a fresh CLI process.
