---
slug: defer-v15-orchestrator-worker-epic-6-tasks-out-of-1-5-1-5-x
task: v15p-release-150
date: "2026-06-14"
edges: []
---

## Decision

Defer v15-orchestrator-worker epic (6 tasks) OUT of 1.5 → 1.5.x/2.0. 1.5 is a hardening release; orchestrator-worker is a new feature abstraction (delegation primitive + sub-agent profile + scope hard-gate + hooks + schema change) that would commit the framework's DB+CLI to a 2.0-line pattern inside a routine release. With it deferred, 1.5 is CODE-COMPLETE (P2 debt cleared, AIDD shipped, memory-strictness + RENAR-lite + BLE001 landed). Only remaining: v15p-release-150 (irreversible publish, needs user go).

## Rationale

Shipping half a new abstraction in a hardening release inverts the risk profile (schema migration + new CLI for a 2.0-line feature). The epic stays fully planned (QG-0-ready) for a dedicated post-1.5 effort. Unblocks a clean 1.5.0 cut now.
