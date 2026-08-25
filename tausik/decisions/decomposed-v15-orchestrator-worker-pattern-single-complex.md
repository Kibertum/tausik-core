---
slug: decomposed-v15-orchestrator-worker-pattern-single-complex
task: null
date: "2026-06-14"
edges: []
---

## Decision

Decomposed v15-orchestrator-worker-pattern (single complex placeholder) into epic v15-orchestrator-worker → story v15-ow-core → 6 QG-0-ready tasks: v15-ow-delegate-cli, v15-ow-subagent-profile, v15-ow-scope-hardgate, v15-ow-hook-recognize, v15-ow-summary-back, v15-ow-docs-tests. Placeholder task deleted.

## Rationale

The item was an architectural epic (6 sub-components) mis-filed as one complex task under the stale v14-polish-followup epic, and prompt.md flagged it for fresh context. A 6-part model-auto-switch abstraction can't be implemented well in one session tail; decomposition is the architect step. Each task now carries goal+AC+scope+scope_exclude+rollback so any fresh session can pick one up. Architecture itself unchanged (auto-switch = orchestrator-worker via Agent tool, complexity<=medium workers, Opus coordinator).
