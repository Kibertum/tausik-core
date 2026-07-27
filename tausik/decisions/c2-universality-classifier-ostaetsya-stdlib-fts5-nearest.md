---
slug: c2-universality-classifier-ostaetsya-stdlib-fts5-nearest
task: v14c-ai-classifier-universality
date: "2026-05-07"
edges: []
---

## Decision

C2 universality classifier остаётся stdlib + FTS5 nearest-neighbor над brain mirror; ML/embedding (sentence-transformers, ChromaDB, ONNX) явно отвергнуты.

## Rationale

CLAUDE.md mandate 'Python 3.11+ stdlib' + memory dead-end #27 (ChromaDB rejected as too heavy). Goal задачи изначально упоминал 'local model или Notion-side embedding', но это конфликтует с stdlib rule. Hybrid scope (расширение regex + FTS5 similarity over существующего brain mirror) даёт synonym detection без новых deps. Reuse scripts/brain_search.py FTS5 + bm25 infrastructure. Implementation: scripts/brain_universality_semantic.py 288L.
