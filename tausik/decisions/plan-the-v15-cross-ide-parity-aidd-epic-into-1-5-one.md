---
slug: plan-the-v15-cross-ide-parity-aidd-epic-into-1-5-one
task: null
date: "2026-06-14"
edges: []
---

## Decision

Plan the v15-cross-ide-parity (AIDD) epic INTO 1.5 — one concrete task per existing story, no invented padding. autogen story → `v15-aidd-autogen-cmd` (CLI drafts vision.md from repo signals, stdlib heuristics, reuses scaffold conflict-handling); ai-validation story → `v15-aidd-validate-cmd` (CLI detects drift between conventions.md machine-checkable claims and repo state, exit≠0 on drift). Both CLI-first, MCP surface deferred to optional P2 follow-ups to avoid doc-count drift.

## Rationale

User explicitly chose "plan into 1.5" over "defer out". The epic was the last blocker to declaring 1.5 scope-complete. Scoped from the actual shipped scaffold (v14b-aidd-scaffold-basic) and the 3 real templates (idea/vision/conventions), so tasks reflect genuine follow-ups, not padding. Kept stdlib-only (no LLM call) consistent with the framework; deferred MCP tool surfaces because each adds ~14 doc-count refs across 10 docs.
