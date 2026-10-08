---
slug: reserch-cubest-onyx-sessiya-138-zaveden-v-1-8-kak-story
task: tool-output-rollup
date: "2026-07-25"
edges: []
---

## Decision

Ресёрч cubest/onyx (сессия #138) заведён в 1.8 как story borrow-cubest-onyx под landscape-2026-h2 — 4 нетто-новых задачи: tool-output-rollup, rag-contextual-chunk-prefix, mcp-scope-tools-exposure, graph-mermaid-render. Пересекающееся НЕ дублируется: гибридный vector-retrieval → brainh-semantic-search + l26-embeddings-revisit; retrieval/narrow-scope → km-* трек; deferred-loading тулов → l26-tool-token-cost. Contextual-prefix детерминированный (метаданные, не LLM-résumé) ради stdlib-first.

## Rationale

Пользователь попросил завести задачи и пересмотреть путь до 1.8. Пересмотр: у половины идей УЖЕ есть трек — дубли раздули бы релиз и создали конфликты. Реконсиляция: новое только где трека нет; существующее усилить (onyx подтверждает скепсис l26-embeddings-revisit: гибрид ценен, embeddings-only мало). Story под landscape-2026-h2 тематически верна, эпиков и так 99.
