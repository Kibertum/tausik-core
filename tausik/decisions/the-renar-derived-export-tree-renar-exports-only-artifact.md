---
slug: the-renar-derived-export-tree-renar-exports-only-artifact
task: renar-tree-gitattributes-lf
date: "2026-06-14"
edges: []
---

## Decision

The RENAR derived export tree (renar/) exports ONLY artifact-derived state — specs, adapts, and a conformance view of level/signals/mandatory-clauses — and deliberately excludes anything that moves for reasons unrelated to RENAR artifacts: write-time dates (assessment-date/manifest-id stay in RENAR-CONFORMANCE.yaml) and operational counters (verification_runs/memory_edges/reasoning_tasks from gather_signals raw-counts). Newlines are pinned to LF via scoped .gitattributes (renar/** eol=lf).

## Rationale

A --check drift gate is only useful if the tree changes exactly when (and only when) a SPEC/ADAPT changes. Embedding dates made it churn daily; embedding operational counters made it churn on every verify/memory op; autocrlf made fresh Windows clones see CRLF-vs-LF false drift. Excluding volatile inputs + pinning eol gives the gate a stable, cross-platform contract. Generalizes the date-free rule (Decision-adjacent memory #162) to all volatile inputs.
