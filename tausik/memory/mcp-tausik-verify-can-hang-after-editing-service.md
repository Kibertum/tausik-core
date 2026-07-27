---
slug: mcp-tausik-verify-can-hang-after-editing-service
title: "MCP tausik_verify can hang after editing service_verification.py — use CLI"
type: gotcha
tags: []
task: null
edges: []
---

After editing scripts/service_verification.py (or any module bootstrap copies into .claude/scripts/), the MCP tausik_verify tool can stall for tens of seconds because the long-running MCP server still holds the pre-edit imports and may hit cache-bypass paths that force inline pytest. The CLI form `.tausik/tausik verify --task <slug>` spawns a fresh Python process and returns in ~2s. Symptom observed in session #46 right after fixing _SECURITY_PATH_TOKENS.

Rule: any time you have just edited verify-path code in-session, switch to CLI verify until the next /start. Always announce verify ahead of running it (it is potentially long).</content>
<parameter name="tags">["mcp", "verify", "qg2", "tooling"]</parameter>
<parameter name="task_slug">v14b-defect-qg2-security-substring-too-broad</parameter>
</invoke>
<invoke name="Grep">
<parameter name="pattern">test_security_paths_detected|TestIsSecuritySensitive
