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
completed_at: null
---

## Goal

Семантический поиск по brain поверх локального индекса: embeddings через локальную модель (Ollama) или лёгкую альтернативу, гибрид с FTS5 (вдохновение: turbovec/iai-mcp из Sortula-закладок). Graceful degradation на чистый FTS5 без embeddings-провайдера. AC: запрос «как мы решали X» находит перефразированные паттерны; latency <2с локально; zero-dependency путь сохранён.

## Acceptance Criteria

1. Запрос вида «как мы решали X» находит перефразированные паттерны — семантический хит там, где чистый FTS5 промахивается.
2. Латентность локального поиска < 2 с.
3. Zero-dependency путь сохранён: без embeddings-провайдера поиск gracefully деградирует до чистого FTS5.
CHANGELOG.md [Unreleased] и зеркало CHANGELOG.ru.md обновлены прозаической записью об этом изменении.

## Plan

## Rollback

## Journal

- 2026-07-20T10:40:42Z [planning] — КАНДИДАТ НА ЗАКРЫТИЕ (решение #153, сессия #120). Прямо оспорена задачей l26-embeddings-revisit, которая приводит отрезвляющие данные отрасли, включая онлайновый A/B Cursor, против ожидаемого выигрыша от embeddings. НЕ закрывать до её результата — решение должно опираться на замер, а не на ожидание. Но приоритет l26-embeddings-revisit поднят именно потому, что её отрицательный результат снимает эту complex-задачу целиком.
