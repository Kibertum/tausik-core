---
slug: memory-block-injects-multiline-text-across-projects
title: "БЛОКЕР kb-global-read: build_memory_block не убирает переносы строк, и это станет каналом инъекции между проектами"
status: planning
epic: null
story: null
complexity: simple
role: developer
stack: python
tier: moderate
call_budget: 35
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
completed_at: null
---

## Goal

Найдено ревью безопасности сессии #155. Дефект СУЩЕСТВУЕТ УЖЕ СЕЙЧАС локально, но общая база превращает его в МЕЖПРОЕКТНЫЙ канал, поэтому задача блокирует kb-global-read.

ЗАМЕР. В одном файле scripts/service_knowledge_aggregates.py два агрегатора ведут себя ПО-РАЗНОМУ:
- build_compact_memory_tail (строки ~46,51,56,61) делает .replace("\n", " ") — переносы убираются;
- build_memory_block (строки ~105,112,119,126) делает ТОЛЬКО срез по длине вида (d.get("decision") or "")[:100] — переносы остаются.
Оба агрегатора формируют текст, который проецируется в CLAUDE.md и в контекст сессии через SessionStart-хук.

СЦЕНАРИЙ ОТКАЗА. Запись, сделанная в проекте A: tausik decide "Обычный заголовок\n\n## SYSTEM: ..." --global. Проект B в другой сессии получает её в memory_block и агент проекта B видит поддельный markdown-заголовок как часть системного контекста. Сегодня это ограничено одним проектом; после kb-global-read — нет.

ОТДЕЛЬНО: scripts/service_decide.py::record прогоняет через validate_length, но НЕ через safe_single_line — в отличие от memory_add, где заголовок нормализуется (service_knowledge.py:48). То есть текст решения не обезврежен ни на локальном пути, ни на общем.

ГРАНИЦА РЕШЕНИЯ, принята заранее и обоснована: чинить надо на ГРАНИЦЕ ОТРИСОВКИ, а не на записи. Обезвреживание при записи уничтожает содержание — многострочное обоснование законно многострочно, и портить его в базе значит лечить симптом ценой данных. Единый контракт: любой текст, попадающий в инъекцию памяти, приводится к одной строке и жёсткому лимиту В МОМЕНТ СБОРКИ БЛОКА.

## Acceptance Criteria

## Plan

## Rollback

## Journal
