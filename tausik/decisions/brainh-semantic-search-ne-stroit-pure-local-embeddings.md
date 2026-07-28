---
slug: brainh-semantic-search-ne-stroit-pure-local-embeddings
task: l26-embeddings-revisit
date: "2026-07-27"
edges: []
---

## Decision

brainh-semantic-search: НЕ строить pure local embeddings сейчас. Пересмотр в FTS5-first ГИБРИД: semantic re-rank ПОВЕРХ keyword, gated by (provider есть)+(запрос natural-language, не короткий keyword)+(база >1000 записей), всегда degrade to FTS5. Вердикты альтернатив: BM25F — уже есть FTS5, усилить field-weighting (keep, cheapest); ast-grep/tree-sitter — для КОДА не для brain-прозы, вне scope (relevant codebase-RAG); LSP symbol-path — для стабильности код-цитат (km-цепочка), отклонить здесь. Мерить на СВОЁМ трафике, не вендор-бенчах.

## Rationale
