---
slug: kb-global-read
title: "Чтение из обеих баз: поиск и старт сессии видят общие знания"
status: planning
epic: shared-knowledge
story: kb-global
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths:
  - "scripts/service_knowledge.py"
  - "scripts/knowledge_db.py"
scope_tools: []
completed_at: null
---

## Goal

Поиск памяти и блок знаний на старте сессии читают ОБЕ базы и выдают объединённый результат с явной пометкой источника (этот проект или общая база). Реализация: рассмотреть ATTACH DATABASE — тогда сервисный слой не дублируется и запросы ходят в обе базы одним соединением; оговорка в том, что FTS5 живёт по базам раздельно, поэтому поиск делается двумя запросами с объединением результатов. Ранжирование: FTS плюс свежесть плюс из скольких проектов запись подтверждена. Ставку на embeddings НЕ делать — измерения отрасли показывают, что короткие ключевые запросы, а это доминирующая форма запроса агента, обрушивают семантический поиск почти до нуля. Общая база недоступна или заблокирована — работаем на проектной, но с видимым предупреждением, а не молча.

## Acceptance Criteria

1. Поиск памяти и блок знаний на старте сессии читают ОБЕ базы и возвращают объединённый результат с явной пометкой источника (этот проект / общая база).
2. Ранжирование учитывает FTS, свежесть и число проектов, подтвердивших запись; embeddings не используются.
3. Недоступность или блокировка общей базы не роняет работу: используется проектная база с ВИДИМЫМ предупреждением, а не молчаливой деградацией.
CHANGELOG.md [Unreleased] и зеркало CHANGELOG.ru.md обновлены прозаической записью об этом изменении.

## Plan

## Rollback

git revert; чтение снова только из проектной БД

## Journal

- 2026-08-02T14:42:00Z [planning] — РАЗВЕДКА ПЕРЕД СТАРТОМ (сессия #155, агент-исследователь). Карта точек чтения и три вывода, меняющие дизайн. ВЫВОД 1 — ОБРАЗЕЦ ПОМЕТКИ ИСТОЧНИКА УЖЕ ЕСТЬ, ИЗОБРЕТАТЬ ВТОРОЙ НЕЛЬЗЯ. Это cq (Mozilla cross-project knowledge), scripts/service_cq_row.py: константа CQ_SOURCE="cq", build_cq_row() возвращает dict с id=None (СОЗНАТЕЛЬНО не 0 — «нет адреса»), source="cq", type="cq" (намеренно ВНЕ VALID_MEMORY_TYPES) и меткой прямо в заголовке. Подмешивается в service_knowledge.memory_search:82-111 дописыванием В ХВОСТ того же списка. Два рендерера УЖЕ умеют это отрисовывать, ветвясь на id is None: harness/claude/mcp/project/handlers_knowledge.py:124 (_format_memory_hit — ЕДИНСТВЕННЫЙ формат-хук строки поиска) и scripts/project_cli_extra.py:52-54. ОГРАНИЧЕНИЕ ОБРАЗЦА: поле source есть ТОЛЬКО у cq-строк, у локальных его нет вовсе, то есть отсутствие ключа сейчас неявно означает «проектная». Ни один рендерер поле source не печатает — различение идёт по id is None и по префиксу в title. ВЫВОД 2 — «СТАРТ СЕССИИ» ЭТО НЕ tausik_session_open. Конверт session_open память НЕ читает вообще (ни memory_block, ни memory_search, ни decisions) и защищён аллоу-листами _SESSION_ENVELOPE_KEYS/_SELF_CHECK_ENVELOPE_KEYS — новое поле в него молча не просочится. Знание приходит агенту ДВУМЯ другими путями: (а) scripts/service_knowledge_aggregates.py:66 build_memory_block -> SessionStart-хук scripts/hooks/session_start.py:210; (б) build_compact_memory_tail:19 -> update_claudemd -> CLAUDE.md и AGENTS.md. По решению про перенос ре-инъекции путь (б) ОСНОВНОЙ, потому что /start больше не дёргает tausik_memory_block. Значит править надо ИМЕННО ЭТИ ДВА, а не конверт. ВЫВОД 3 — ЛИМИТЫ ВЫТЕСНЯТ ПРОЕКТНУЮ ПАМЯТЬ, ЕСЛИ ПРОСТО ПОДМЕШАТЬ. build_memory_block жёстко 5 решений / 10 конвенций / 5 дед-эндов / 5 контекстов, build_compact_memory_tail жёстко 5/5/3/5 БЕЗ параметров вообще, сортировка ORDER BY id DESC. Общая база имеет СВОЮ нумерацию, поэтому «свежесть по id» между базами несопоставима в принципе. Подмешивание в ту же квоту вытеснит проектные записи молча. РЕШЕНИЕ ПРИНИМАТЬ ЯВНО: отдельная секция под общие записи со своей квотой, а не слияние в общую. ОГРАНИЧЕНИЕ, КОТОРОЕ НАДО СОБЛЮСТИ: tests/test_knowledge_write.py:62,70,176 утверждают svc.memory_list() == [] после записи с --global. Это НЕ помеха, а граница дизайна: memory_list — перечисление ПРОЕКТНОЙ памяти, и оно обязано остаться проектным. AC говорит «ПОИСК и старт сессии видят обе базы», а не «перечисление». Если тронуть memory_list, три этих теста покраснеют — и покраснеют ПРАВИЛЬНО. ТОЧКИ ЧТЕНИЯ, КОТОРЫЕ ОБЯЗАНЫ НАУЧИТЬСЯ ВИДЕТЬ ОБЩУЮ БАЗУ (полный перечень из разведки): - scripts/service_knowledge.py:82 memory_search (сюда же уже подмешивается cq — тот же шов) - scripts/backend_queries.py:123 search_all -> ProjectService.search:199 -> CLI cmd_search (project_cli_ops.py:101) и MCP _handle_search (handlers_status.py:85) - scripts/service_knowledge_aggregates.py:66 build_memory_block и :19 build_compact_memory_tail - ВТОРОЙ НЕЗАВИСИМЫЙ КАНАЛ, легко пропустить: harness/claude/mcp/codebase-rag/rag_handlers.py:218 search_knowledge — тоже через be.search_all, со СВОИМ форматтером _format_knowledge_results:65 - сниппеты: scripts/snippet_storage.py:130 search_snippets_ranked -> MCP _do_snippet_search (handlers_status.py:153); работает НАПРЯМУЮ с svc.be._conn, минуя сервисный слой ТЕСТЫ, КОТОРЫЕ СЛОМАЮТСЯ ПРИ СМЕНЕ ФОРМЫ ВЫДАЧИ (проверить до правки): test_memory_cq_rows.py (самый чувствительный — фиксирует провенанс построчно), test_memory_block.py, test_memory_context_surfacing.py, test_claudemd_drift.py (стаб-бэкенд с сигнатурой memory_list(self, mtype, limit) — сломается от ЛЮБОГО нового аргумента), test_snippet_mcp_search.py (фиксирует ровно 6 ключей конверта), плюс test_tausik_backend.py:513-596 и test_project_mcp.py:239,304-307.
