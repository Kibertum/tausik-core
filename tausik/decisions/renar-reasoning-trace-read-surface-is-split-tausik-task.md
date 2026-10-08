---
slug: renar-reasoning-trace-read-surface-is-split-tausik-task
task: v16r-task-replay
date: "2026-06-13"
edges: []
---

## Decision

RENAR reasoning-trace read surface is split: tausik task show prints the raw trace; tausik task replay merges it with logs/events/verification into one chronological markdown timeline. The replay backend reader lives in backend_crud_reasoning.py (not backend_queries.py) and goes through the service layer (self.reasoning_steps/self.events_list).

## Rationale

Keeps RENAR backend reads thematically cohesive and avoids growing the already-oversized backend_queries.py (461 lines) past the 400-line filesize gate. Service-layer routing preserves the CLI→service→backend layering. Replay is read-only and works on historical tasks (graceful empty sources), so it carries no migration and is safe to ship on the 1.x track.
