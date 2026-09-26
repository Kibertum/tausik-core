---
slug: rag-language-list-is-hardcoded-while-stacks-are-user-extensible
title: "RAG не видит языки, которые TAUSIK признаёт стеками: список расширений захардкожен, ручки нет (GitLab #11)"
status: done
epic: release-110-deferred-from-19
story: release110-tracker-promises
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "harness/claude/mcp/codebase-rag/rag_languages.py"
  - "harness/claude/mcp/codebase-rag/rag_detect.py"
  - "harness/claude/mcp/codebase-rag/rag_indexer.py"
  - "harness/claude/mcp/codebase-rag/rag_handlers.py"
  - "tests/test_rag_languages.py"
  - "tests/test_rag_reindex_progress.py"
scope_paths:
  - "harness/claude/mcp/codebase-rag/*.py"
  - "tests/*.py"
  - "docs/ru/*.md"
  - "docs/en/*.md"
  - "CHANGELOG*.md"
scope_tools: []
depends_on: []
completed_at: "2026-09-23T19:21:01Z"
resolution: null
resolution_reason: null
---

## Goal

ПРИШЛО ИЗ ТРЕКЕРА: GitLab #11 (открыт 28.08, автор ayumashev, ноль комментариев). Задачи не было — проверено поиском по slug и по тексту.

ЗАМЕР ПОТРЕБИТЕЛЯ (проект taiga-whisper, Godot 4): codebase-rag индексирует документацию и оснастку и НИ ОДНОГО файла игры. rag_status до правки: 2027 чанков / 126 файлов, языки markdown 1392, python 470, json 133, yaml 27, gitignore 4, toml 1 — питон здесь это tools/ генерации ассетов, маркдаун — дизайн-доки. search_code по любому имени функции из godot/scripts/ отдаёт пусто, и агент откатывается на Grep — ровно против чего таблица маршрутизации инструментов в CLAUDE.md его отговаривает.

ГДЕ: harness/claude/mcp/codebase-rag/rag_detect.py — EXT_TO_LANG (56 расширений в 1.8.0), нет .gd/.gdshader/.tscn/.tres/.godot. harness/claude/mcp/codebase-rag/rag_indexer.py — _BOUNDARY_PATTERNS (12 языков), нет gdscript. detect_language() возвращает None, файл выпадает в get_file_list() и до чанкинга не доходит.

ПРОВЕРЕНО АВТОРОМ, ЧТО ПРАВКА РАБОТАЕТ: после пяти расширений и четырёх boundary-паттернов 2594 чанка / 180 файлов, gdscript 283, godot-scene 207, gdshader 13, godot-resource 6, godot-project 2; search_code "whisper cooldown spirit summon" первым результатом отдаёт тело _trigger_summon() целиком с верными границами. Мусор не попал: .godot/ отсекается gitignore, .import/.uid/бинарники не имеют записи в EXT_TO_LANG (0 совпадений по rag_chunks).

КОРЕНЬ, НАЗВАННЫЙ АВТОРОМ, И ОН ШИРЕ ЧАСТНОГО СЛУЧАЯ: список СТЕКОВ расширяется пользователем штатно (.tausik/stacks/<name>/), а список ЯЗЫКОВ RAG — нет. TAUSIK признаёт стек godot, которого его собственный RAG не видит. Эта асимметрия и есть дефект; пять расширений — лишь её сегодняшнее проявление (за ним стоят Unity: .cs есть, .unity/.asset/.prefab нет, — Unreal и любой самописный стек).

НА СТОРОНЕ ПОТРЕБИТЕЛЯ НЕ ЛЕЧИТСЯ: .tausik/ переживает bootstrap, .claude/mcp/ — нет, bootstrap_copy.copy_dir() перезаписывает деплой из harness/. Механизма override для MCP-серверов не существует (harness/overrides/<ide>/rules.md покрывает только текст правил CLAUDE.md). Единственный способ удержать правку — патчить сабмодуль и реаплаить после каждого submodule update, то есть та же болезнь, что в GitLab #10 (три правки живут патчами поверх пина).

РАЗВИЛКА, КОТОРУЮ НЕ РЕШАТЬ В ОДИНОЧКУ: (1) дописать пять расширений и четыре паттерна во встроенный список — дёшево, но следующий движок придёт снова; (2) дать конфиг-ручку rag.extra_extensions / rag.boundaries в .tausik/config.json, читаемую из rag_detect/rag_indexer, — лечит корень (асимметрию стеков и языков) и закрывает Unity/Unreal/самописные стеки заодно. Автор тикета склоняется ко (2). Цена (2) — валидация пользовательских регулярок и поведение при кривой ручке; тихо падать в None она права не имеет.

## Acceptance Criteria

1. Встроенно: .gd (gdscript), .gdshader, .tscn (godot-scene), .tres (godot-resource), .godot (godot-project) распознаются, у gdscript/gdshader/сцен есть boundary-паттерны; тест на детекторе и на чанкинге функции GDScript.
2. Ручка в .tausik/config.json: rag.extra_extensions {".ext": "language"} и rag.boundaries {"language": "regex"} читаются rag_detect/rag_indexer проекта, для которого строится индекс; тест: расширение из ручки индексируется, его файл режется по заданной границе.
3. НЕГАТИВНЫЙ: кривая ручка (расширение без точки, пустой язык, некомпилируемая регулярка, не-словарь) не роняет индексацию и не пропадает молча: запись пропускается, причина видна в rag_status; тест на каждый вид.
4. НЕГАТИВНЫЙ: ручка не отменяет встроенное и не расширяет индексацию на бинарники: .import/.uid и файлы без записи по-прежнему не индексируются.
5. docs (configuration en/ru), CHANGELOG EN+RU.

## Plan

## Rollback

Правка аддитивна: записи во встроенных списках и необязательный блок rag.* в config.json; откат — git revert и reindex

## Journal

- 2026-09-23T19:19:16Z [implementation] — AC-1: ✓ tests/test_rag_languages.py::test_godot_files_are_built_in
- 2026-09-23T19:19:16Z [implementation] — Сделано: harness/claude/mcp/codebase-rag/rag_languages.py (встроенный Godot: 5 расширений, 4 границы; load() читает rag.extra_extensions/rag.boundaries из .tausik/config.json проекта и возвращает problems); rag_detect.detect_language(extra), get_file_list читает ручку; rag_indexer.chunk_file(boundaries), index_full/index_incremental передают ручку; rag_status отдаёт language_config. Развилка тикета: сделаны оба пути (встроенный Godot и ручка), правка аддитивна. 15 новых тестов, 126 тестов RAG зелёные.
- 2026-09-23T19:19:17Z [implementation] — AC-1: ✓ tests/test_rag_languages.py::test_a_gdscript_function_is_one_chunk_with_its_body
- 2026-09-23T19:19:17Z [implementation] — AC-2: ✓ tests/test_rag_languages.py::test_the_project_knob_adds_an_extension_and_its_boundary
- 2026-09-23T19:19:18Z [implementation] — AC-3: ✓ tests/test_rag_languages.py::test_a_bad_knob_is_skipped_and_reported_never_silent
- 2026-09-23T19:19:18Z [implementation] — AC-3: ✓ tests/test_rag_languages.py::test_rag_status_shows_the_knob_and_its_problems
- 2026-09-23T19:19:18Z [implementation] — AC-4: ✓ tests/test_rag_languages.py::test_the_knob_cannot_override_a_built_in
- 2026-09-23T19:19:19Z [implementation] — AC-4: ✓ tests/test_rag_languages.py::test_godot_side_files_stay_out
- 2026-09-23T19:19:19Z [implementation] — AC-5: ✓ docs/en|ru/configuration.md, CHANGELOG EN+RU
