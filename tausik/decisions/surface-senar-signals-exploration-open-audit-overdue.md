---
slug: surface-senar-signals-exploration-open-audit-overdue
task: null
date: "2026-05-06"
edges: []
---

## Decision

Surface SENAR signals (exploration_open, audit_overdue_sessions) directly in tausik_status compact JSON instead of restoring tausik_explore_current + tausik_audit_check to /start Phase 1 batch.

## Rationale

Token-economy: enriching one existing call beats adding two more parallel calls. The compact JSON's "fields absent when clean" contract means zero noise overhead in normal state; signals only appear when actionable. Also unblocks the future v14b-session-open-compound-rpc work (compound RPC inherits enriched status). Trade-off: backend layering — handler-level lookup of svc.exploration_current() and svc.audit_overdue_sessions() — accepted because both are pure read-only service calls already exposed.</rationale>
<parameter name="task_slug">v14b-status-exploration-audit-signals
