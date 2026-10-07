---
slug: per-test-provenance-granularity-is-a-declared-non-goal-of
task: fix-pooled-verify-recovery-ss4-widening-inputs
date: "2026-10-07"
edges: []
---

## Decision

Per-test provenance granularity is a declared non-goal of the verification-cohort contract: cohort identity binds content digests and gate signature, NOT per-test selection lists

## Rationale

Wiring per-test provenance would couple cohort identity to pytest's collection order and make every deselection an identity break; the pooled receipt's honesty lives in files coverage + gate signature + named refusals, which the tests pin. AC-4 wording narrowed accordingly; schema stays v76 without a provenance column.
