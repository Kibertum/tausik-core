---
slug: test-count-cross-file-scanner-uses-narrow-context-tight
task: v14b-doc-gen-test-count
date: "2026-05-06"
edges: []
---

## Decision

Test-count cross-file scanner uses narrow context-tight regex (pytest suite (N tests) | badge URL tests-N%20passed | badge label [!N tests] | **N tests** bold) — NOT a generic \b\d+ tests?\b — to keep false-positive rate near zero on illustrative phrases.

## Rationale

Generic pattern catches both authoritative test counts and illustrative numbers in the same prose (e.g. AGENTS.md "Never add 5 tests where one parametrized test covers the same matrix"). Narrow patterns trade a bit of coverage for high signal-to-noise. New count phrasings can be added incrementally; false alarms cost agent time on every CI run.
