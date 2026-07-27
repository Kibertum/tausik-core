---
slug: reverse-decision-116-implement-v15-orchestrator-worker-epic
task: v15-ow-delegate-cli
date: "2026-06-14"
edges: []
---

## Decision

REVERSE Decision #116: implement v15-orchestrator-worker epic INTO 1.5 (user direction). TAUSIK provides delegation SCAFFOLDING/STATE (`task delegate` + handoff contract + recognition hook + worker scope hard-gate + summary-back); the agent does the actual Agent-tool spawn (only programmatic model-selection Claude Code exposes). Build 6 v15-ow-* tasks in dependency order, ship incrementally (each additive). Lite: reuse scope-ACL + hook + model-routing, minimal schema delta.

## Rationale

User chose to carry orchestrator in 1.5. Owning prior call: defer was partly scope-avoidance; fresh budget makes it buildable incrementally/additively (no big-bang), weakening the defer rationale.
