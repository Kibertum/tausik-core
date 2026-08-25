---
slug: rag-contextual-chunk-prefix
title: "RAG-качество: детерминированный contextual-prefix к чанку перед индексацией (заимствование onyx/Anthropic)"
status: done
epic: landscape-2026-h2
story: borrow-cubest-onyx
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 60
defect_of: null
scope: "harness/claude/mcp/codebase-rag/: новый rag_context.py (построение префикса), rag_store.py (колонка context_prefix + FTS + триггеры + миграция существующих БД), rag_indexer.py (передача сводки модуля). scripts/ — скрипт воспроизводимого замера retrieval. tests/. CHANGELOG EN+RU."
scope_exclude: "НЕ трогать формат выдачи search() — префикс не должен попасть в отображаемый контент (AC4), значит SELECT остаётся на r.content. НЕ вводить LLM-вызовы: префикс детерминированный из метаданных, это явное требование задачи (stdlib-first, воспроизводимость). НЕ трогать memory FTS (.tausik/tausik.db) — задача допускает «codebase-RAG и/или memory», беру только codebase-RAG, чтобы замер был на одном индексе. НЕ менять пороги/лимиты поиска."
relevant_files:
  - "harness/claude/mcp/codebase-rag/rag_context.py"
  - "harness/claude/mcp/codebase-rag/rag_store.py"
  - "harness/claude/mcp/codebase-rag/rag_indexer.py"
  - "scripts/rag_retrieval_bench.py"
  - "tests/test_rag_context_prefix.py"
  - pyproject.toml
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths:
  - "harness/claude/mcp/codebase-rag/"
  - "scripts/"
  - "tests/"
  - pyproject.toml
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-07-28T15:00:55Z"
---

## Goal

Поднять попадаемость retrieval, предваряя каждый индексируемый чанк (codebase-RAG и/или memory FTS) коротким ДЕТЕРМИНИРОВАННЫМ контекст-заголовком (путь файла + имя символа/секции + тип), чтобы изолированный чанк не терял контекст документа — техника contextual retrieval (onyx/Anthropic), но БЕЗ LLM-вызова (детерминированные метаданные, а не сгенерированное résumé — держим stdlib-first и воспроизводимость). Обязателен baseline-замер ДО/ПОСЛЕ на воспроизводимом наборе запросов. Reconcile с km-retrieval-baseline-eval (переиспользовать его метрику, если готов).

## Acceptance Criteria

1. Зафиксирован baseline retrieval-метрики ДО (воспроизводимый набор запросов → одна цифра); reuse km-retrieval-baseline-eval если готов. 2. Каждый чанк индексируется с ДЕТЕРМИНИРОВАННЫМ контекст-префиксом (путь файла + имя символа/секции + тип); тот же вход → тот же префикс байт-в-байт. 3. Замер ПОСЛЕ на том же наборе: retrieval не хуже baseline (цель — лучше), цифры записаны в задачу. 4. НЕГАТИВ: префикс НЕ протекает в отображаемый агенту контент (живёт только в индексе) — поиск возвращает исходный чанк, а не заголовок; чанк без метаданных индексируется корректно, без пустого/битого префикса. 5. ИДЕМПОТЕНТНОСТЬ: повторная индексация без изменений источника даёт тот же индекс. 6. Полный scoped verify зелёный.

## Plan

## Rollback

git revert коммита задачи. Схема rag.db меняется аддитивно (ALTER TABLE ADD COLUMN + пересоздание FTS-таблицы, которая является производным индексом, а не источником данных), поэтому откат безопасен: после revert старый код пересоздаст FTS из rag_chunks, лишняя колонка context_prefix останется неиспользуемой и ничему не помешает. Полное восстановление в любом случае доступно командой `tausik` reindex — индекс целиком выводим из исходников. Проверка отката: search_code возвращает результаты.

## Journal

- 2026-07-28T14:59:12Z [implementation] — ЗАМЕР ДО/ПОСЛЕ (AC1 + AC3). Инструмент: scripts/rag_retrieval_bench.py, воспроизводимый — запросы выводятся МЕХАНИЧЕСКИ из корпуса (не пишутся руками, поэтому набор нельзя подогнать под лестный результат), выборка детерминированная (фиксированный шаг 2, без RNG). Корпус: 353 файла scripts/ + bootstrap/. Метрика: recall@K по КОНКРЕТНОМУ ЧАНКУ (совпадение файла И попадание целевой строки в диапазон возвращённого чанка). Два набора: context (запрос = слова о чём ФАЙЛ + идентификатор из чанка в середине файла — случай, ради которого заголовок и заводится) и control (запрос ТОЛЬКО из слов, уже присутствующих в теле чанка — здесь заголовок помогать не должен, а главное не должен ВРЕДИТЬ, потому что добавление текста в индекс разбавляет частоту терминов). Результат при n=115 на набор: K=3 context 0.4870 -> 0.8348 (delta +0.3478), control 0.5739 -> 0.6435 (+0.0696); K=5 context 0.7043 -> 0.9739 (+0.2696), control 0.6870 -> 0.7391 (+0.0521); K=10 context 0.8783 -> 1.0000 (+0.1217), control 0.8087 -> 0.8348 (+0.0261). Регрессии нет ни на одном K ни в одном наборе; выигрыш максимален при K=3, то есть там, где агент реально читает выдачу. ДВЕ ЛОЖНЫЕ ВЕРСИИ ЗАМЕРА, отброшенные по пути, фиксирую честно: (1) первая версия считала попадание ПО ФАЙЛУ — при 353 файлах и K=10 набор context упёрся в потолок recall=1.0000 и в baseline, и с префиксом, то есть метрика была насыщена и не могла показать НИ улучшения, ни регрессии; (2) на той же насыщенной метрике control показал -0.0666, что выглядело как доказательство вреда, а после перехода на попадание по чанку и увеличения выборки с n=30 до n=115 знак стал устойчиво положительным — при n=30 один перевернувшийся запрос давал +-0.033, то есть прежний минус был шумом малой выборки. Вывод, который стоит запомнить: насыщенная метрика и малая выборка одинаково опасны, но по-разному — первая не показывает ничего, вторая показывает случайное.
- 2026-07-28T15:00:46Z [implementation] — AC-1: ✓ baseline зафиксирован одной цифрой на воспроизводимом наборе — scripts/rag_retrieval_bench.py, 353 файла, 115 запросов на набор, recall@3 context=0.4870 / control=0.5739 (числа и метод в отдельной записи журнала). km-retrieval-baseline-eval переиспользовать не удалось: существующий tests/test_rag_benchmark.py меряет ПРОПУСКНУЮ СПОСОБНОСТЬ, а не качество выдачи, поэтому метрика построена заново. AC-2: ✓ tests/test_rag_context_prefix.py::test_prefix_is_byte_identical_across_runs, ::test_prefix_carries_path_words_and_symbol_words, ::test_module_summary_reaches_every_chunk_not_just_the_first, ::test_continuation_chunk_inherits_the_enclosing_symbol — префикс детерминированный (путь + символ + тип + сводка модуля), без единого вызова модели. AC-3: ✓ замер ПОСЛЕ на том же наборе: K=3 context +0.3478 / control +0.0696; K=5 +0.2696 / +0.0521; K=10 +0.1217 / +0.0261. Требование «не хуже baseline» выполнено с запасом на обоих наборах при каждом K. AC-4: ✓ tests/test_rag_context_prefix.py::test_search_returns_the_source_chunk_never_the_header, ::test_header_is_searchable_even_though_it_is_not_returned, ::test_chunk_without_metadata_gets_a_usable_prefix_not_a_broken_one — префикс живёт в собственной колонке, search() отдаёт r.content, поэтому протечь структурно не может; чанк без метаданных получает префикс только из слов пути, а не пустой или битый. AC-5: ✓ tests/test_rag_context_prefix.py::test_reindexing_unchanged_source_yields_an_identical_index — повторная индексация без изменений источника даёт побайтово тот же набор строк. AC-6: ✓ verification_run #1567 (green, exit=0); ruff clean, mypy Success 314 файлов (потребовало override для rag_context/rag_indexer/rag_store — импорт через sys.path.insert не разрешается mypy), filesize exit 0, срез 611 тестов rag/mcp/web_cache зелёный, bootstrap --ide all прогнан, doctor «OK All clean». Domain: результат проверен на НАСТОЯЩЕМ индексе проекта, а не только на фикстурах: миграция pre-v2 базы прошла на живом .tausik/rag/rag.db — колонка context_prefix добавлена, все 15876 чанков сохранены, поиск возвращает результаты, ключа context_prefix в выдаче нет. Миграция закреплена и тестом tests/test_rag_context_prefix.py::test_pre_v2_database_gains_the_column_and_keeps_its_rows, который проверяет именно то, что установленный индекс НЕ опустошается апгрейдом (FTS-таблица пересоздаётся с новым списком колонок и перестраивается из rag_chunks — источника истины). ПОБОЧНО ИСПРАВЛЕНО: annotate_chunks читает chunk.get('content') вместо chunk['content'] — заглушка в tests/test_rag_reindex_progress передаёт чанки без этого ключа, и KeyError убивал бы индексацию ЦЕЛОГО файла из-за одного чанка; тонкий заголовок лучше потерянного индекса.
