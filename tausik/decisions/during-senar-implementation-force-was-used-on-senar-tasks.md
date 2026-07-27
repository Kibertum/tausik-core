---
slug: during-senar-implementation-force-was-used-on-senar-tasks
task: null
date: "2026-03-23"
edges: []
---

## Decision

During SENAR implementation, --force was used on SENAR tasks themselves because QG-0/QG-2 gates didn't exist when tasks were created. This is a known bootstrapping paradox: you can't enforce gates that don't exist yet. Going forward, ALL tasks must have goal+AC set during /plan, and --force is reserved for supervisor emergency override only.

## Rationale

SENAR tasks were created before QG-0 existed, so they had no AC. The gates were added mid-implementation, creating a chicken-and-egg problem.
