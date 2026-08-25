---
slug: snippets-taxonomy-kind-is-free-text-not-check-constrained
task: v15-snippet-classifier
date: "2026-06-13"
edges: []
---

## Decision

snippets.taxonomy_kind is free TEXT (not CHECK-constrained) and the snippet classifier is advisory-only auto-fill

## Rationale

Taxonomy is an advisory hint set by a heuristic classifier, not a RENAR closed list — a hard CHECK would reject future kinds and a wrong inference must never block a brain write. Auto-fill only fires when caller omitted the key + knob on + category patterns/gotchas, never overwrites.
