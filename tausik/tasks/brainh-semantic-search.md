---
slug: brainh-semantic-search
title: "[P1] Brain semantic search (локальные embeddings)"
status: planning
epic: shared-knowledge
story: km-knowledge-layer
complexity: complex
role: developer
stack: python
tier: substantial
call_budget: 100
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

[ПЕРЕСМОТРЕНО l26-embeddings-revisit / решение #191 — было: pure local embeddings через Ollama.] Гибрид FTS5-first вместо pure embeddings. Отрезвляющие данные: онлайн-A/B Cursor (2025-11-06) — офлайн +12.5% точности, но реальное удержание кода +0.3% в целом и лишь +2.6% на базах >1000 файлов; Sourcegraph УБРАЛ embeddings в пользу BM25F поверх code-graph; короткие ключевые запросы (доминирующая форма агента) обрушивают семантику до nDCG@10≈0; CORE-Bench (июнь 2026): выигрывает гибрид, ни один метод не доминирует. Цель: FTS5/BM25 остаётся спиной (уже есть), semantic — ОПЦИОНАЛЬНЫЙ re-rank ПОВЕРХ, включаемый только когда (a) провайдер присутствует, (b) запрос natural-language (не короткий keyword), (c) база достаточно большая. Всегда graceful degrade к чистому FTS5. Замер эффекта — на СВОЁМ трафике (LoCoMo дискредитирован), внешний ориентир BEAM. Вердикты альтернатив: BM25F — усилить field-weighting FTS5 (title>tags>content), самое дешёвое; ast-grep/tree-sitter — для КОДА, не brain-прозы (см. codebase-RAG); LSP symbol-path — для стабильности код-цитат (km-цепочка), не сюда.

## Acceptance Criteria

1. Semantic поиск — re-rank ПОВЕРХ FTS5, а НЕ замена: FTS5-путь работает всегда; запрос «как мы решали X» получает семантический буст там, где чистый FTS5 промахивается, но короткий ключевой запрос обслуживается keyword-путём (провал семантики на nDCG@10≈0 не должен деградировать keyword-результат).
2. Латентность локального поиска < 2 с; semantic-слой gated by размером базы (включается только когда стоит по объёму — эффект embeddings <3% и сконцентрирован в базах >1000 записей).
3. НЕГАТИВНЫЙ/граничный: без embeddings-провайдера ИЛИ на коротком ключевом запросе — graceful degrade к чистому FTS5 без ошибки и без пустого результата (zero-dependency путь сохранён).
4. Эффект измеряется на СВОЁМ трафике, а не вендорских бенчмарках (LoCoMo дискредитирован: baseline без памяти обошёл Mem0 73:68).
CHANGELOG.md [Unreleased] и зеркало CHANGELOG.ru.md обновлены прозаической записью.

## Plan

## Rollback

## Journal

- 2026-07-20T10:40:42Z [planning] — КАНДИДАТ НА ЗАКРЫТИЕ (решение #153, сессия #120). Прямо оспорена задачей l26-embeddings-revisit, которая приводит отрезвляющие данные отрасли, включая онлайновый A/B Cursor, против ожидаемого выигрыша от embeddings. НЕ закрывать до её результата — решение должно опираться на замер, а не на ожидание. Но приоритет l26-embeddings-revisit поднят именно потому, что её отрицательный результат снимает эту complex-задачу целиком.
- 2026-07-27T17:23:56Z [planning] — ТЗ ПЕРЕСМОТРЕНО l26-embeddings-revisit (решение #191): pure local embeddings → FTS5-first гибрид, semantic как опциональный re-rank поверх keyword, gated by provider+query-type+base-size, degrade to FTS5. НЕ закрыта: гибрид с семантикой-поверх остаётся жизнеспособным для больших баз, но приоритет и объём резко урезаны. Замер обязателен на своём трафике до реализации.
