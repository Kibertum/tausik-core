---
slug: gen-doc-constants-cross-file-scanners-version-ref-mcp
task: v14b-doc-gen-test-count
date: "2026-05-06"
edges: []
---

## Decision

gen_doc_constants cross-file scanners (version-ref, MCP-counts, test-count) all strip fenced code blocks before scanning. Drift inside fenced blocks (e.g. AGENTS.md repo-layout `pytest suite (X tests)` rendered in a fenced overview) is intentionally invisible and must be fixed manually.

## Rationale

Doc examples often cite outdated counts on purpose (snapshots, "before"/"after" demos, history). A fence-blind scanner would force every code-as-illustration to match live state — high false-positive cost. Rare structural-overview drifts inside fences are handled manually during normal doc reviews. Trade-off chosen for false-positive control.
