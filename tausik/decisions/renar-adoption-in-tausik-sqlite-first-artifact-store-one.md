---
slug: renar-adoption-in-tausik-sqlite-first-artifact-store-one
task: null
date: "2026-06-14"
edges: []
---

## Decision

RENAR adoption in TAUSIK: sqlite-first artifact store + one-way file export (no separate doc service), realistic honest target RENAR-3 (core-mode), and RENAR strengthens SENAR by making ADAPT backward-findings + spec-version-pinned verification part of QG-0/QG-2.

## Rationale

Inventory shows the RENAR substrate is ~90% built already: specs (typed, FTS), adapts (forward interpret §7.4.3 / backward closed-7 findings / dual-sign ed25519 §7.5 / delta §7.6 / link), renar_drift gate, renar_conformance honest self-assessment. Current status is pre-adoption (level:null) blocked SOLELY by adapt-per-tz=false (no real ADAPT data) — not by missing machinery. Three gaps: (1) no file export (the ONE thing the user named); (2) no real ТЗ/ADAPT data (adoption); (3) not wired into the agent workflow. Substrate model: sqlite = single source of truth (live, mutable); events hash-chain (v34) = V1 immutable history + V6 author/timestamp; one-way git-exported renar/ tree = V3 diff&review + V4 branching + V5 version-pin (derived view, NEVER hand-edited — matches RENAR 'knowledge graph as derived view'). Unlike Kai we run no separate service: `tausik renar export [--check]` (like doc-constants) regenerates the tree from DB, git tracks it. Honest target is RENAR-3 (the independent audit's economically-realistic ceiling); TAUSIK is solo so dual-signature ADAPT is core-mode and the conformance generator keeps us honest (no box-ticking). The POINT is quality: ADAPT backward-findings (gap/contradiction/hidden-assumption) become a stronger QG-0 'context before code' gate for substantial/deep tiers, and verifies_version_pin makes a green mean 'verified against requirement vX', not just 'tests pass'. ai-provenance is a cheap RENAR-4 win — TAUSIK already tracks model/cost/tokens via usage_events.
