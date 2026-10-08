---
slug: renar-adoption-is-advisory-first-lite-tausik-is-a
task: renar-qg0-adapt-context-gate
date: "2026-06-14"
edges: []
---

## Decision

RENAR adoption is ADVISORY-FIRST ('lite') — TAUSIK is a lightweight zero-dep framework. Ladder: (1) artifacts SPEC/ADAPT/conformance [done, RENAR-1]; (2) advisory — QG-0 nudges 'high-stakes task (substantial/deep) without linked SPEC/ADAPT', non-blocking, config-toggle, default on [1.5]; (3) hard-gate only when a real defect traces to its absence [2.0]; (4) RENAR-2 signed/immutable ADAPT, irreversible+user-directed [2.0]. Deliberate lightweight policy, not 'unfinished RENAR'.

## Rationale

Lightweight framework must not impose heavy mandatory ceremony. Hard-gating now (#91 audit) adds friction with no evidence it prevents bugs; RENAR-2 crypto-lock must never ride a routine release. Advisory-first makes interpretation visible at QG-0 while keeping the agent unblocked: fail-soft on advisory, fail-closed only on proven gates. Ladder tells dev when to climb.
