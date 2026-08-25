---
slug: do-not-integrate-cq-sdk-as-dependency-keep-existing-stdlib
task: cq-rag-research
date: "2026-04-08"
edges: []
---

## Decision

Do NOT integrate CQ SDK as dependency. Keep existing stdlib-only cq_client.py. Enhance FTS5 RAG with web search cache and knowledge indexing instead.

## Rationale

CQ SDK requires pydantic + httpx (violates stdlib-only). CQ is 0.x.x with expected breaking changes. TAUSIK already has a working stdlib-only CQ client. Better ROI: enhance existing FTS5 RAG with web cache table (60-80% token savings on repeated searches) and knowledge FTS indexing (20-30% savings). Total estimated savings: 40-60% per session.
