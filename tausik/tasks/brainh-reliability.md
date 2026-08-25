---
slug: brainh-reliability
title: "Notion как опциональный двусторонний sync: offline-очередь + local-first + health"
status: planning
epic: shared-knowledge
story: kb-notion
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

Локальный KB — источник истины. Когда Notion включён, синхронизировать с ним двусторонне: local-first запись (никогда не блокируем на сети), offline-очередь для отложенной доставки, health-сигнал состояния синхронизации в doctor. Разрешение конфликтов детерминировано (local wins по умолчанию, с журналом расхождений). Часть KB-трека 1.8 (перенесено из brain-hardening по решению «Notion остаётся опцией»).

## Acceptance Criteria

1. Локальный KB — источник истины; запись local-first НИКОГДА не блокируется на сети (тест: при недоступном Notion запись проходит немедленно).
2. При включённом Notion работает двусторонняя синхронизация; отложенная доставка идёт через offline-очередь.
3. Разрешение конфликтов детерминировано (local wins по умолчанию) с журналом расхождений.
4. doctor показывает health-сигнал состояния синхронизации (в норме / очередь не пуста / ошибка).
CHANGELOG.md [Unreleased] и зеркало CHANGELOG.ru.md обновлены прозаической записью об этом изменении.

## Plan

## Rollback

## Journal

- 2026-07-20T10:40:42Z [planning] — КАНДИДАТ НА ЗАКРЫТИЕ (решение #153, сессия #120). Решает ту же проблему, что kb-notion-publisher, но противоположным способом: делает Notion надёжнее ВНУТРИ критического пути агента (offline-очередь, retry, health), тогда как shared-knowledge убирает Notion из критического пути вовсе. Второй подход строго лучше: он снимает класс отказа, а не смягчает его. Закрывать после того, как kb-notion-publisher принят к работе.
