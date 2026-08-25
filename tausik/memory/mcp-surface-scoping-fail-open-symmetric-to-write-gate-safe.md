---
slug: mcp-surface-scoping-fail-open-symmetric-to-write-gate-safe
title: "MCP surface scoping: fail-open, symmetric to write-gate, safe-core as prefix families"
type: pattern
tags:
  - borrow-onyx
  - fail-open
  - mcp
  - scope
  - senar-rule2
task: mcp-scope-tools-exposure
edges: []
---

mcp-scope-tools-exposure: filtering the MCP tool-list by the active task's scope_tools ACL follows the SAME shape as scope_write_gate. (1) Fail-open by construction: feature flag off (default) / no active task / no active task declared non-empty scope_tools / any error → expose ALL tools. Legacy freedom = ALL are undeclared (symmetric to l26-hook-contract-review AC3: an undeclared co-active task does NOT restore full freedom once a sibling declared). (2) always-safe-core = expose unconditionally so the agent can never lock itself out: prefix families tausik_task_* + tausik_session_* + singletons {status,verify,doctor,health,self_check,update_claudemd,*_search}. Prefix families survive tool add/remove; a ratchet test asserts SAFE_CORE_EXACT ⊆ real TOOLS names so a rename reddens CI instead of silently stranding the agent. (3) Hiding is UX/token only, NOT the security barrier — call_tool + write-gate are untouched, so a hidden tool called directly still passes existing enforcement. Measured: 117 tools/43.7KB → 40/19.3KB (56% cut) for a typical scope. list_tools computes the scoped set at call time; live mid-session re-scope via tools/list_changed is deferred to l26-tool-token-cost (orthogonal: one shapes the list, the other changes when the host loads it).
