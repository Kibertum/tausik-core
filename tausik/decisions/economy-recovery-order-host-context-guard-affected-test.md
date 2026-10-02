---
slug: economy-recovery-order-host-context-guard-affected-test
task: retrospektiva-rashoda-codex-1-11-kontekst-tool
date: "2026-10-01"
edges: []
---

## Decision

Economy recovery order: host-context guard, affected-test selection, bounded validation output, evidence-based test pruning, then r111 economy acceptance.

## Rationale

The guard prevents another runaway thread first; selection and bounded output reduce feedback cost before pruning; pruning then uses cheaper validation; acceptance measures the resulting natural work.
