---
slug: cross-file-version-ref-scanner-targets-a-fixed-list-of-6
task: v14b-doc-gen-cross-files
date: "2026-05-06"
edges: []
---

## Decision

Cross-file version-ref scanner targets a fixed list of 6 top-level marketing docs (README x2, AGENTS, CLAUDE, architecture x2) rather than walking all of docs/

## Rationale

Marketing/intro docs are the highest-value drift targets - readers form first impressions there. Scanning all of docs/ would multiply false positives (deep technical docs intentionally reference historical versions). Fixed list keeps signal-to-noise high; expansion is cheap when needed.
