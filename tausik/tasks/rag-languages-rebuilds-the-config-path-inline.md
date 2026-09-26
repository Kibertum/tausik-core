---
slug: rag-languages-rebuilds-the-config-path-inline
title: "rag_languages собирает путь .tausik/config.json вручную вместо tausik_config_path — ловит тест test_no_inline_duplicates_in_production"
status: done
epic: release-110-deferred-from-19
story: release110-rag-and-memory-tell-the-truth
complexity: simple
role: developer
stack: python
tier: trivial
call_budget: null
defect_of: rag-language-list-is-hardcoded-while-stacks-are-user-extensible
scope: null
scope_exclude: null
relevant_files:
  - "harness/claude/mcp/codebase-rag/rag_languages.py"
  - "tests/test_rag_languages.py"
scope_paths:
  - "harness/claude/mcp/codebase-rag/rag_languages.py"
  - "tests/*.py"
  - "CHANGELOG*.md"
scope_tools: []
depends_on: []
completed_at: "2026-09-23T21:19:04Z"
resolution: null
resolution_reason: null
---

## Goal

Путь к конфигу проекта в RAG-ручке берётся из tausik_utils.tausik_config_path, как требует храповик; модуль импортирует помощник и в развёрнутой раскладке (.claude/mcp/codebase-rag → .claude/scripts), и в исходной (harness/claude/mcp/codebase-rag → scripts), и в фоновом переиндексе, где sys.path несёт только каталог RAG.

## Acceptance Criteria

1. tests/test_tausik_utils.py::test_no_inline_duplicates_in_production зелёный (до правки красный на rag_languages.py).
2. tests/test_rag_languages.py зелёный, в том числе когда в sys.path только каталог RAG (фоновый переиндекс).
3. НЕГАТИВНЫЙ: если помощник не найден ни в одной раскладке, ручка сообщает об этом в problems, а не падает и не молчит.

## Plan

## Rollback

git revert одной правки

## Journal

- 2026-09-23T20:47:27Z [implementation] — AC-1: ✓ tests/test_tausik_utils.py::test_no_inline_duplicates_in_production
- 2026-09-23T20:47:27Z [implementation] — AC-2: ✓ tests/test_rag_languages.py::test_the_config_path_comes_from_the_shared_helper
- 2026-09-23T20:47:27Z [implementation] — Найдено verify-прогоном соседней задачи: tests/test_tausik_utils.py::test_no_inline_duplicates_in_production красный на rag_languages.py (мой код задачи rag-language-list...). Правка: _config_path ищет scripts/ в развёрнутой (2 уровня) и исходной (4 уровня) раскладках и берёт tausik_config_path; помощник не найден — запись в problems. Проверено импортом при sys.path без scripts.
- 2026-09-23T20:47:28Z [implementation] — AC-3: ✓ tests/test_rag_languages.py::test_a_missing_config_helper_is_reported_not_silent
- 2026-09-23T20:47:28Z [implementation] — NO-DEAD-END: дефект найден храповиком, исправлен первым же подходом
- 2026-09-23T21:18:57Z [implementation] — Root cause: при написании rag_languages я прочёл конфиг путём, собранным вручную, не проверив, что в репозитории есть единственный помощник tausik_config_path и храповик test_no_inline_duplicates_in_production; RAG-сервер живёт вне scripts/, и импорт помощника там не очевиден, поэтому путь был продублирован. Исправлено поиском scripts/ в обеих раскладках.
