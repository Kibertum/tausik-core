---
slug: "1-11-transport-rule-one-projectservice-implementation-two"
task: mcp-first-rule-versus-skills-over-cli
date: "2026-10-01"
edges: []
---

## Decision

1.11 transport rule: one ProjectService implementation, two thin wrappers; skills choose the workflow, fresh MCP is preferred for atomic agent operations, and CLI is the explicit stale/unavailable/CLI-only fallback

## Rationale

Live Codex shows both transports can occupy one outer model tool round and can be batched; MCP gives typed arguments and 39 ms median in a 10-call probe, while fresh CLI avoids stale loaded code but paid 439 ms process-start median. Token and retry parity remain unknown, so transport priority is not sold as token savings.
