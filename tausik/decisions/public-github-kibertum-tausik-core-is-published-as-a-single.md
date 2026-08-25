---
slug: public-github-kibertum-tausik-core-is-published-as-a-single
task: github-publish-v153
date: "2026-06-15"
edges: []
---

## Decision

Public github (Kibertum/tausik-core) is published as a SINGLE orphan commit with no development history; the full history lives only on the private gitlab mirror. Each public release re-orphans from the current tree and force-pushes; ALL legacy tags are purged so no leak/history is reachable from any github ref.

## Rationale

User direction: keep internal development history (decisions, leak-bearing old commits) off the public repo; an orphan + tag purge is the only way to make the public tree AND history leak-free. gitlab keeps the auditable full history for internal work.
