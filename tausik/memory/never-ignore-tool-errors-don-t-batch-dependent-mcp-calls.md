---
slug: never-ignore-tool-errors-don-t-batch-dependent-mcp-calls
title: "Never ignore tool errors; don't batch dependent MCP calls"
type: convention
tags:
  - anti-drift
  - dogfooding
  - mcp
  - slug-validation
  - workflow
task: null
edges: []
---

When a TAUSIK MCP tool returns an error, the agent must:
1. Name the root cause out loud (first sentence of next response)
2. Fix it — don't retry blindly, don't silently continue
3. Only then proceed with dependent calls

Strict chain — never batch in parallel: task_add → task_update → task_plan → task_start. Each needs the previous to succeed; one error kills the chain and leaves orphan failures.

Slug validation: must match `^[a-z0-9][a-z0-9-]*$`. No dots, no slashes, no versions like 'v1.2'. Sanitize mentally: 'v1.2-foo' → 'v12-foo' or 'v1-2-foo'. As of 2026-04-17, validate_slug in scripts/tausik_utils.py returns a suggested alternative in the error message (`Did you mean '{sanitized}'?`) — read it.

If a tool errors mid-sequence: STOP, state the error, fix it, then resume from that step — do NOT restart from the top.

Why this is a TAUSIK memory (convention) not a Claude auto-memory: this rule is specific to TAUSIK's MCP call semantics and DB validation. Framework-specific behavioral rules belong in project memory and get re-injected via memory_block on every /start and SessionStart hook — that keeps enforcement near the tools, not in a user's home directory.
