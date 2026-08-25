---
slug: v15mr-phase-matrix-phase-complexity-matrix-is-authoritative
task: v15mr-phase-matrix
date: "2026-06-14"
edges: []
---

## Decision

v15mr-phase-matrix: phase×complexity matrix is authoritative; implement-simple routes to Sonnet (not Haiku). 3 legacy simple→haiku assertions updated; haiku preserved under research-simple.

## Rationale

AC1 (matrix per ТЗ: implement simple=sonnet) and AC2 (existing tests green) conflict irreducibly, since legacy suggest_model('simple')→haiku and no-phase==implement. Resolved in favor of the explicit matrix: Haiku is too weak for production code edits, so implement-floor is Sonnet; Haiku is reserved for research-simple (read-only discovery). AC2 honored as signature/consumer back-compat (single-arg calls still work); the 3 simple-tier test assertions are updated to the new intended routing, with a new research-phase test preserving the haiku mapping. Documented for audit honesty.
