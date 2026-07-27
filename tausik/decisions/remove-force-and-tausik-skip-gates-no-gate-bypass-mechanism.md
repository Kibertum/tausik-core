---
slug: remove-force-and-tausik-skip-gates-no-gate-bypass-mechanism
task: null
date: "2026-04-07"
edges: []
---

## Decision

Remove --force and TAUSIK_SKIP_GATES — no gate bypass mechanism in production

## Rationale

Gate bypasses undermine SENAR enforcement. Tests use fixture-based mocking (conftest.py) and config-based gate disabling instead of env var bypass. Breaking change — document in release notes.
