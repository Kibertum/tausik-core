---
slug: compound-mcp-rpc-best-effort-envelope-with-inline-error-keys
title: "Compound MCP RPC: best-effort envelope with inline error keys"
type: pattern
tags:
  - compound-rpc
  - envelope-pattern
  - mcp
  - token-economy
task: v14b-session-open-compound-rpc-impl
edges: []
---

When collapsing N parallel MCP calls into a single compound RPC for token economy:
1. Wrap EACH sub-call in its own try/except — never let one failure abort the envelope.
2. On sub-call failure, return that section as `{"error": str(e)}` instead of dropping the key — agent can render a degraded dashboard.
3. Always include all expected top-level keys (assert in test). Missing keys force the agent to defensive-check; error-keyed sections let it keep going.
4. Reuse existing handler logic where possible (e.g. `json.loads(_handle_status({"compact":true}))`) — wasteful re-serialization is one-time cost, but DRY beats divergence.
5. Add schema entry to tools_extra.py (no input args for /start-style aggregators) and dispatch entry in _DISPATCH of BOTH harnesses (claude+cursor must stay byte-identical via cp).
6. Update doc-constants.json and tool counts in AGENTS.md / README{.ru}.md / docs/{en,ru}/mcp.md / docs/{en,ru}/senar-compliance-matrix.md / docs/README.md.

Reference impl: harness/claude/mcp/project/handlers.py:_handle_session_open (v14b-session-open-compound-rpc-impl).
