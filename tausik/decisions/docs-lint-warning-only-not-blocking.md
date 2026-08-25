---
slug: docs-lint-warning-only-not-blocking
task: null
date: "2026-04-26"
edges: []
---

## Decision

Docs lint warning-only, not blocking

## Rationale

User: 'линт в ворнинг'. Allows incremental cleanup without blocking PRs. Many '(v1.2)' annotations are factual feature-added markers, not stale claims — hard-block would generate false positives.
