---
slug: no-package-refactoring-keep-flat-scripts-directory-for-v1-0
task: null
date: "2026-04-06"
edges: []
---

## Decision

No package refactoring — keep flat scripts/ directory for v1.0

## Rationale

3 independent experts confirmed: 22 files / 5400 lines don't need subpackages. ROI negative, risk of breaking 765 tests + bootstrap + MCP for marginal gain.
