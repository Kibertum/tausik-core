---
slug: rag-index-never-prunes-deleted-paths
title: "Индекс RAG не вычищает удалённые файлы: search_code первым результатом отдаёт путь, которого нет"
status: done
epic: release-110-deferred-from-19
story: release110-rag-and-memory-tell-the-truth
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "harness/claude/mcp/codebase-rag/rag_indexer.py"
  - "harness/claude/mcp/codebase-rag/rag_store.py"
  - "tests/test_rag_prune_dead_paths.py"
scope_paths:
  - "harness/claude/mcp/codebase-rag/*.py"
  - "tests/*.py"
  - "CHANGELOG*.md"
scope_tools: []
depends_on: []
completed_at: "2026-09-23T19:29:37Z"
resolution: null
resolution_reason: null
---

## Goal

НАЙДЕНО ЗАМЕРОМ В #189 при домере издержек задачи four-byte-identical-copies-of-the-harness. Проверено ВЫЗОВОМ, не рассуждением.

ЗАМЕР. В .tausik/rag/rag.db 18917 чанков по 3507 различным файлам. Из этих 3507 путей 62 НЕ СУЩЕСТВУЮТ на диске: 56 под agents/ (каталог, которого в дереве нет вовсе — обвязка давно живёт в harness/), 4 под scripts/, по одному в .github/ и tests/. rag_meta: schema_version 2, last_commit 29e3958, last_indexed 2026-08-29T11:29:09Z — то есть индекс СВЕЖИЙ и всё равно несёт мёртвые пути.

ТИХАЯ ОШИБКА ВОСПРОИЗВОДИТСЯ ПЕРВЫМ ЖЕ ЗАПРОСОМ. `fts_code MATCH 'brain_store_decision'` отдаёт по возрастанию rank: agents/claude/mcp/brain/handlers.py (НЕ СУЩЕСТВУЕТ), agents/cursor/mcp/brain/handlers.py (НЕ СУЩЕСТВУЕТ), затем harness/claude/mcp/brain/handlers.py (существует). Два первых результата — мёртвые пути. Агент, которому CLAUDE.md предписывает предпочитать search_code Grep-у, получает первым ответом файл, которого нет, и узнаёт об этом только когда Read падает.

МЕХАНИЗМ (гипотеза, требует подтверждения кодом, а не принимается на веру): инкрементальный переиндекс идёт от rag_meta.last_commit и обновляет/добавляет изменённые файлы, но УДАЛЁННЫЕ пути из rag_chunks и fts_code не вычищает. Переименование каталога agents/ -> harness/ поэтому оставило старую копию рядом с новой, и обе живут в индексе одновременно.

ПОБОЧНОЕ НАБЛЮДЕНИЕ, ВАЖНОЕ ДЛЯ four-byte-identical-copies-of-the-harness: среди мёртвых путей есть agents/cursor/..., то есть ЗЕРКАЛА когда-то индексировались. Сегодня — нет: живых чанков под .claude/, .cursor/, .qwen/, .kilo/, .opencode/, .kilocode/ РОВНО НОЛЬ. Утверждение цели той задачи «поиск индексирует их» на сегодня ЛОЖНО, а 56 мёртвых чанков — след того времени, когда оно было истинным.

ЧТО ДЕЛАЕТСЯ: переиндекс обязан удалять записи о путях, которых больше нет (по списку удалённых из git diff между last_commit и HEAD, либо сверкой существования при инкрементальном проходе). НЕГАТИВНОЕ: доказывать двусторонне — удалить файл, переиндексировать, убедиться, что его чанки ИСЧЕЗЛИ из rag_chunks И из fts_code (две таблицы, вычищать надо обе); и убедиться, что живой файл при этом не потерян.

## Acceptance Criteria

1. Причина подтверждена кодом: _get_changed_files делит строку git diff --name-status один раз, и строка переименования R100<TAB>old<TAB>new попадает в modified как один путь 'old<TAB>new' — старый путь не удаляется, новый не индексируется. Тест воспроизводит на git-репозитории до правки.
2. Переименование: старый путь уходит из rag_chunks И из fts_code, новый индексируется; копирование (C) индексирует новый и не трогает старый.
3. Сверка существования: инкрементальный проход удаляет из индекса каждый путь, которого нет на диске, — так вычищаются и мёртвые пути, накопленные до правки.
4. НЕГАТИВНЫЙ: живой файл при сверке не теряется; путь, вышедший за пределы проекта, не трогается; tests двусторонние (удалённый исчез из обеих таблиц, живой остался).
5. CHANGELOG EN+RU.

## Plan

## Rollback

Правка в переиндексаторе harness/claude/mcp/codebase-rag/; откат git revert. Данные восстановимы полным переиндексом (reindex), схема rag.db не меняется.

## Journal

- 2026-09-23T19:28:38Z [implementation] — Причина подтверждена кодом и тестом до правки: _get_changed_files делил строку по первому TAB; на строке R100 old new deleted=[] (тест test_a_rename_line_is_read_as_two_paths красный до правки). Правка: разбор R/C с двумя путями; _prune_missing сверяет существование каждого индексированного пути (и в ветке 'нет изменений'); RAGStore.indexed_paths. Живой индекс: до — 3645 путей, 123 мёртвых (agents/..., .github/...); прогон исправленного index_incremental: files_pruned=123; после — 3522 пути, 0 мёртвых.
- 2026-09-23T19:28:39Z [implementation] — AC-1: ✓ tests/test_rag_prune_dead_paths.py::test_a_rename_line_is_read_as_two_paths
- 2026-09-23T19:28:39Z [implementation] — AC-2: ✓ tests/test_rag_prune_dead_paths.py::test_a_renamed_file_leaves_both_tables_and_the_new_one_is_indexed
- 2026-09-23T19:28:39Z [implementation] — AC-3: ✓ tests/test_rag_prune_dead_paths.py::test_a_path_already_dead_in_the_index_is_pruned_and_a_live_one_kept
- 2026-09-23T19:28:40Z [implementation] — AC-4: ✓ tests/test_rag_prune_dead_paths.py::test_a_path_already_dead_in_the_index_is_pruned_and_a_live_one_kept (живые keep.py, handlers.py, new.py остаются в обеих таблицах; путь вне проекта _safe_path отсекает)
- 2026-09-23T19:28:40Z [implementation] — AC-5: ✓ CHANGELOG EN+RU
