---
slug: rag-index-never-prunes-deleted-paths
title: "Индекс RAG не вычищает удалённые файлы: search_code первым результатом отдаёт путь, которого нет"
status: planning
epic: null
story: null
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
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

НАЙДЕНО ЗАМЕРОМ В #189 при домере издержек задачи four-byte-identical-copies-of-the-harness. Проверено ВЫЗОВОМ, не рассуждением.

ЗАМЕР. В .tausik/rag/rag.db 18917 чанков по 3507 различным файлам. Из этих 3507 путей 62 НЕ СУЩЕСТВУЮТ на диске: 56 под agents/ (каталог, которого в дереве нет вовсе — обвязка давно живёт в harness/), 4 под scripts/, по одному в .github/ и tests/. rag_meta: schema_version 2, last_commit 29e3958, last_indexed 2026-08-29T11:29:09Z — то есть индекс СВЕЖИЙ и всё равно несёт мёртвые пути.

ТИХАЯ ОШИБКА ВОСПРОИЗВОДИТСЯ ПЕРВЫМ ЖЕ ЗАПРОСОМ. `fts_code MATCH 'brain_store_decision'` отдаёт по возрастанию rank: agents/claude/mcp/brain/handlers.py (НЕ СУЩЕСТВУЕТ), agents/cursor/mcp/brain/handlers.py (НЕ СУЩЕСТВУЕТ), затем harness/claude/mcp/brain/handlers.py (существует). Два первых результата — мёртвые пути. Агент, которому CLAUDE.md предписывает предпочитать search_code Grep-у, получает первым ответом файл, которого нет, и узнаёт об этом только когда Read падает.

МЕХАНИЗМ (гипотеза, требует подтверждения кодом, а не принимается на веру): инкрементальный переиндекс идёт от rag_meta.last_commit и обновляет/добавляет изменённые файлы, но УДАЛЁННЫЕ пути из rag_chunks и fts_code не вычищает. Переименование каталога agents/ -> harness/ поэтому оставило старую копию рядом с новой, и обе живут в индексе одновременно.

ПОБОЧНОЕ НАБЛЮДЕНИЕ, ВАЖНОЕ ДЛЯ four-byte-identical-copies-of-the-harness: среди мёртвых путей есть agents/cursor/..., то есть ЗЕРКАЛА когда-то индексировались. Сегодня — нет: живых чанков под .claude/, .cursor/, .qwen/, .kilo/, .opencode/, .kilocode/ РОВНО НОЛЬ. Утверждение цели той задачи «поиск индексирует их» на сегодня ЛОЖНО, а 56 мёртвых чанков — след того времени, когда оно было истинным.

ЧТО ДЕЛАЕТСЯ: переиндекс обязан удалять записи о путях, которых больше нет (по списку удалённых из git diff между last_commit и HEAD, либо сверкой существования при инкрементальном проходе). НЕГАТИВНОЕ: доказывать двусторонне — удалить файл, переиндексировать, убедиться, что его чанки ИСЧЕЗЛИ из rag_chunks И из fts_code (две таблицы, вычищать надо обе); и убедиться, что живой файл при этом не потерян.

## Acceptance Criteria

## Plan

## Rollback

Правка в переиндексаторе harness/claude/mcp/codebase-rag/; откат git revert. Данные восстановимы полным переиндексом (reindex), схема rag.db не меняется.

## Journal
