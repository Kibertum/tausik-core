---
slug: borrow-cubest-onyx
title: "Заимствования из ландшафта H2'2026: cubest (token-эргономика) + onyx (RAG/MCP-паттерны)"
status: done
epic: landscape-2026-h2
---

Продуктовый ресёрч (сессия #138) двух опенсорс-продуктов: cubest (stateless OLAP-агрегатор для сжатия вывода инструментов AI-агентам, 7-22× токенов) и onyx/Danswer (enterprise RAG-платформа). Из них отобраны НЕТТО-НОВЫЕ идеи, у которых в TAUSIK ещё нет трека. РЕКОНСИЛЯЦИЯ с существующим (не дублировать): гибридный BM25+vector retrieval → уже brainh-semantic-search + l26-embeddings-revisit (со скепсисом к embeddings); narrow-knowledge-scope и retrieval-качество → уже km-* трек; deferred-loading тул-дефиниций → уже l26-tool-token-cost. Здесь только 4 задачи без существующего трека: (1) rollup вербозного вывода инструментов [cubest], (2) contextual-prefix к чанку для RAG/памяти [onyx], (3) экспозиция MCP-тулов по scope_tools задачи [onyx], (4) diagram-as-code (mermaid) рендер графов [cubest]. Все — python, локальный SQLite+FTS5, stdlib-first.
