---
slug: brainh-semantic-search
title: "[P1] Brain semantic search (локальные embeddings)"
status: done
epic: release-110-deferred-from-19
story: deferred-110-knowledge-lifecycle
complexity: complex
role: developer
stack: python
tier: substantial
call_budget: 100
defect_of: null
scope: "Опциональный семантический re-rank ПОВЕРХ существующего FTS5/BM25F. FTS5-путь не меняется по смыслу: расширяется окно кандидатов, порядок пересобирается только когда ворота открыты. Провайдер — по HTTP через urllib, без зависимостей. Замер — свой сайдкар с объявленным сроком жизни."
scope_exclude: "Замена FTS5 на embeddings; жёсткая зависимость на провайдера; изменение веса bm25 (10/1/3 уже стоит); ast-grep и LSP (это про код, не про прозу)."
relevant_files:
  - "scripts/semantic_rerank.py"
  - "tests/test_semantic_rerank.py"
  - "scripts/knowledge_read.py"
  - "scripts/publication_boundary.py"
  - "tests/test_publication_boundary.py"
  - "scripts/telemetry_retention.py"
  - "docs/ru/semantic-rerank.md"
  - "docs/en/semantic-rerank.md"
scope_paths:
  - "scripts/semantic_rerank.py"
  - "tests/test_semantic_rerank.py"
  - "scripts/knowledge_read.py"
  - "scripts/publication_boundary.py"
  - "tests/test_publication_boundary.py"
  - "scripts/telemetry_retention.py"
  - "tests/test_telemetry_retention.py"
  - "tausik/gates.json"
  - "docs/ru/semantic-rerank.md"
  - "docs/en/semantic-rerank.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-09-28T21:35:51Z"
resolution: null
resolution_reason: null
tracker_refs:
  - "github#61"
started_model_id: claude-opus-5
started_model_version: null
done_model_id: claude-opus-5
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
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

git revert. Слой аддитивен: без провайдера и при закрытых воротах путь совпадает с текущим байт в байт, что закрепляет негативный тест. Откат не теряет данных — сайдкар только пишется, ничего не читает из него код поиска.

## Journal

- 2026-07-20T10:40:42Z [planning] — КАНДИДАТ НА ЗАКРЫТИЕ (решение #153, сессия #120). Прямо оспорена задачей l26-embeddings-revisit, которая приводит отрезвляющие данные отрасли, включая онлайновый A/B Cursor, против ожидаемого выигрыша от embeddings. НЕ закрывать до её результата — решение должно опираться на замер, а не на ожидание. Но приоритет l26-embeddings-revisit поднят именно потому, что её отрицательный результат снимает эту complex-задачу целиком.
- 2026-07-27T17:23:56Z [planning] — ТЗ ПЕРЕСМОТРЕНО l26-embeddings-revisit (решение #191): pure local embeddings → FTS5-first гибрид, semantic как опциональный re-rank поверх keyword, gated by provider+query-type+base-size, degrade to FTS5. НЕ закрыта: гибрид с семантикой-поверх остаётся жизнеспособным для больших баз, но приоритет и объём резко урезаны. Замер обязателен на своём трафике до реализации.
- 2026-09-28T21:24:59Z [implementation] — НАХОДКА ЧУЖОЙ ПРОВЕРКИ, не моей: test_publication_boundary поймал semantic_rerank как модуль, который читает общее хранилище и пишет наружу без границы. Это не ложное срабатывание — embed() отправляет СОДЕРЖИМОЕ строк на HTTP-точку, и если её направить на хостинг, каждый кандидат уезжает с машины нередактированным. Ровно тот класс утечки, который закрыло решение #358. Чиню по существу: правило «точка эмбеддингов обязана быть loopback» ставится В ГРАНИЦУ, потому что смысл границы — одно место, решающее «можно ли этому уехать». Расширяю scope на scripts/publication_boundary.py и его тест.
- 2026-09-28T21:34:50Z [implementation] — AC-1 (re-rank ПОВЕРХ, не замена): ✓ tests/test_semantic_rerank.py::TestFusionReordersAndNeverRetrieves — страница всегда перестановка того, что вернул FTS5; RRF, а не принятие семантического порядка (ключевой лидер остаётся на странице, семантический фаворит поднимается). Короткий ключевой запрос обслуживается keyword-путём: ::TestTheQueryShapeGate, шесть форм, включая пять голых существительных — длина одна пропустила бы их. AC-2 (латентность < 2 с, ворота по размеру базы): ✓ ::TestTheLatencyBudgetIsRealAndNotAspirational — замер 20 живых поисков: медиана 6,3 мс, p95 46,2 мс. MIN_CORPUS_ROWS=1000, ворота small-corpus.
- 2026-09-28T21:34:51Z [implementation] — AC-3 НЕГАТИВНЫЙ (graceful degrade): ✓ ::TestAClosedGateCostsNothing — три закрытых ворот, провайдера НЕ трогают (embedder падает AssertionError, если позван), порядок совпадает с ключевым, ошибки нет, пусто не возвращается. ✓ ::TestAFailingProviderDegrades — мёртвая точка, не та форма ответа, не то число векторов, нечисловые значения, превышение бюджета: всё сводится к ключевому порядку. Окно кандидатов НЕ расширяется без провайдера (::test_the_candidate_window_stays_at_the_page_size_with_no_provider) — выключенная возможность не должна стоить ничего.
- 2026-09-28T21:34:51Z [implementation] — AC-4 (замер на СВОЁМ трафике): ✓ scripts/semantic_rerank.py --probe на живой машине: 45 живых строк против порога 1000 = 4,5%, провайдер не настроен, обе формы запроса встречают закрытые ворота. Частота срабатывания НОЛЬ — это находка, а не пробел. Инструментировать выключенный путь отказался сознательно: запись в файл на каждый поиск ради факта, который размер базы уже называет. --report читает сайдкар, когда провайдер появится. Domain: ворота и отказ точки проверены на живом хранилище и живом конфиге, не только на фикстуре. Лента: 12164 прошли, 30 пропущены (было 12094), +70 тестов.
