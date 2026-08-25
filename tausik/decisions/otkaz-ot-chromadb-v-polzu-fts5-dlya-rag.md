---
slug: otkaz-ot-chromadb-v-polzu-fts5-dlya-rag
task: null
date: "2026-03-14"
edges: []
---

## Decision

Отказ от ChromaDB в пользу FTS5 для RAG.

## Rationale

ChromaDB требует pip install chromadb + embeddings. FTS5 встроен в SQLite, покрывает keyword search. Для semantic search можно добавить позже как опциональный модуль.
