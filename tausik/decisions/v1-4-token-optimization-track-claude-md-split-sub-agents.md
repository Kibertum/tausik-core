---
slug: v1-4-token-optimization-track-claude-md-split-sub-agents
task: null
date: "2026-05-03"
edges: []
---

## Decision

v1.4 token-optimization track (CLAUDE.md split + sub-agents + AIDD scaffold + active-time session) ships Claude-only. Cursor/Qwen parity is explicitly deferred to v1.5.

## Rationale

User directive (session #50): focus optimization on Claude first, validate token wins with measurements, then port to other IDEs once shape is stable. Avoids 3x bootstrap surface churn during exploration phase.
