---
slug: brainh-capture-ux
title: "[P2] Brain auto-capture: nudge на task done / session end"
status: planning
epic: shared-knowledge
story: km-knowledge-layer
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 60
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

Знания уходят в brain систематически, а не по памяти агента: при task done с непустыми dead ends/decisions и на session end предлагать brain_store_* (эскалирующий nudge из v15p-escalating-nudges, не hard). Фильтр brain.ignored уже существует — переиспользовать. AC: nudge с конкретным draft-содержимым; one-call подтверждение; счётчик captured/skipped в metrics.

## Acceptance Criteria

1. На task done с непустыми dead ends/decisions и на session end предлагается brain_store_* с КОНКРЕТНЫМ draft-содержимым (эскалирующий nudge, не hard).
2. Подтверждение захвата — в один вызов (one-call); фильтр brain.ignored переиспользуется.
3. В metrics появляется счётчик captured/skipped.
CHANGELOG.md [Unreleased] и зеркало CHANGELOG.ru.md обновлены прозаической записью об этом изменении.

## Plan

## Rollback

## Journal

- 2026-07-20T10:40:43Z [planning] — КАНДИДАТ НА ЗАКРЫТИЕ со СЛИЯНИЕМ (решение #153, сессия #120). Идея — систематический захват знаний вместо опоры на память агента — верна и уже частично работает БЕЗ brain: nudge 'No knowledge captured' на task done сработал в сессии #120 и дал шесть записей памяти. Смысл переносится в kb-global-promote (предложение повысить запись при повторе в разных проектах), сам тикет закрывается как привязанный к выводимому brain-стеку.
