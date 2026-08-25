---
slug: tausik-session-open-compound-rpc-orchestrator-placed-in
task: v14b-session-open-compound-rpc-impl
date: "2026-05-06"
edges: []
---

## Decision

tausik_session_open compound RPC orchestrator placed in handler layer (not service layer). Each sub-section (session/status/handoff/tasks/self_check) wrapped in try/except with inline error key sentinel — envelope never aborts on sub-call failure.

## Rationale

self_check is a harness-local module (lives next to handlers.py for module-resolution reasons), not a script — placing the compound in service layer would force a layering violation. Best-effort design lets /start render a degraded dashboard rather than crash, matching the existing _handle_self_check error-key pattern. Token economy: 5 round-trips → 1 (status compact already includes exploration_open + audit_overdue_sessions from v14b-status-exploration-audit-signals, so the compound just needs to bundle session + handoff + tasks split + self_check on top).</rationale>
</invoke>
<invoke name="mcp__tausik-project__tausik_memory_add">
<parameter name="type">gotcha
