---
slug: skills-maturity-architecture-3-layer-context-system-role
task: null
date: "2026-03-14"
edges: []
---

## Decision

Skills maturity architecture: 3-layer context system (role profiles + stack guides + Phase 0 loading). Roles modify skill behavior, stacks provide framework-specific guidance. Bootstrap copies roles always, stacks filtered by detection. Custom frontmatter not supported by IDE — all metadata in body text.

## Rationale

Roles and stacks were dead metadata. Now they drive agent behavior through context injection into skill prompts. 17 validated stacks, 4 role profiles with per-skill modifiers.
