---
slug: brainh-reliability
title: "[SUPERSEDED] Notion bidirectional sync"
status: done
epic: shared-knowledge
story: kb-notion
complexity: complex
role: developer
stack: python
tier: trivial
call_budget: 5
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "tausik/tasks/brainh-reliability.md"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-09-12T13:33:28Z"
resolution: null
resolution_reason: null
---

## Goal

Исходная реализация Notion sync НЕ выполняется: предмет снят решением владельца #358, которое удаляет Notion целиком. Терминальный результат этой задачи — зафиксированная отмена без продуктовых изменений; необходимое удаление выполняется отдельно в [1.9] remove-the-notion-wizard-token-cascade-and-project-registry.

## Acceptance Criteria

AC-1: решение #358 и замена задачей удаления Notion зафиксированы в журнале. AC-2: не добавлены offline queue, retry, health signal или двусторонняя синхронизация. AC-3 (negative): задача не заявляет, что исходные функциональные AC реализованы.

## Plan

## Rollback

## Journal

- 2026-07-20T10:40:42Z [planning] — КАНДИДАТ НА ЗАКРЫТИЕ (решение #153, сессия #120). Решает ту же проблему, что kb-notion-publisher, но противоположным способом: делает Notion надёжнее ВНУТРИ критического пути агента (offline-очередь, retry, health), тогда как shared-knowledge убирает Notion из критического пути вовсе. Второй подход строго лучше: он снимает класс отказа, а не смягчает его. Закрывать после того, как kb-notion-publisher принят к работе.
- 2026-09-12T10:44:09Z — SUPERSEDED terminal disposition: owner decision #358 removes Notion entirely. Original AC are retired, not implemented; replacement is the approved 1.9 removal task.
- 2026-09-12T10:44:19Z — AC verified for terminal disposition: 1) decision #358 and replacement task are recorded; 2) no Notion sync implementation was added; 3) original functional AC are explicitly retired, not claimed.
