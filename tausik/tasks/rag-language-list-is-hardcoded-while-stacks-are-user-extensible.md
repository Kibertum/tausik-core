---
slug: rag-language-list-is-hardcoded-while-stacks-are-user-extensible
title: "RAG не видит языки, которые TAUSIK признаёт стеками: список расширений захардкожен, ручки нет (GitLab #11)"
status: planning
epic: release-19-agent-effectiveness
story: the-loop-closes-outward
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

ПРИШЛО ИЗ ТРЕКЕРА: GitLab #11 (открыт 28.08, автор ayumashev, ноль комментариев). Задачи не было — проверено поиском по slug и по тексту.

ЗАМЕР ПОТРЕБИТЕЛЯ (проект taiga-whisper, Godot 4): codebase-rag индексирует документацию и оснастку и НИ ОДНОГО файла игры. rag_status до правки: 2027 чанков / 126 файлов, языки markdown 1392, python 470, json 133, yaml 27, gitignore 4, toml 1 — питон здесь это tools/ генерации ассетов, маркдаун — дизайн-доки. search_code по любому имени функции из godot/scripts/ отдаёт пусто, и агент откатывается на Grep — ровно против чего таблица маршрутизации инструментов в CLAUDE.md его отговаривает.

ГДЕ: harness/claude/mcp/codebase-rag/rag_detect.py — EXT_TO_LANG (56 расширений в 1.8.0), нет .gd/.gdshader/.tscn/.tres/.godot. harness/claude/mcp/codebase-rag/rag_indexer.py — _BOUNDARY_PATTERNS (12 языков), нет gdscript. detect_language() возвращает None, файл выпадает в get_file_list() и до чанкинга не доходит.

ПРОВЕРЕНО АВТОРОМ, ЧТО ПРАВКА РАБОТАЕТ: после пяти расширений и четырёх boundary-паттернов 2594 чанка / 180 файлов, gdscript 283, godot-scene 207, gdshader 13, godot-resource 6, godot-project 2; search_code "whisper cooldown spirit summon" первым результатом отдаёт тело _trigger_summon() целиком с верными границами. Мусор не попал: .godot/ отсекается gitignore, .import/.uid/бинарники не имеют записи в EXT_TO_LANG (0 совпадений по rag_chunks).

КОРЕНЬ, НАЗВАННЫЙ АВТОРОМ, И ОН ШИРЕ ЧАСТНОГО СЛУЧАЯ: список СТЕКОВ расширяется пользователем штатно (.tausik/stacks/<name>/), а список ЯЗЫКОВ RAG — нет. TAUSIK признаёт стек godot, которого его собственный RAG не видит. Эта асимметрия и есть дефект; пять расширений — лишь её сегодняшнее проявление (за ним стоят Unity: .cs есть, .unity/.asset/.prefab нет, — Unreal и любой самописный стек).

НА СТОРОНЕ ПОТРЕБИТЕЛЯ НЕ ЛЕЧИТСЯ: .tausik/ переживает bootstrap, .claude/mcp/ — нет, bootstrap_copy.copy_dir() перезаписывает деплой из harness/. Механизма override для MCP-серверов не существует (harness/overrides/<ide>/rules.md покрывает только текст правил CLAUDE.md). Единственный способ удержать правку — патчить сабмодуль и реаплаить после каждого submodule update, то есть та же болезнь, что в GitLab #10 (три правки живут патчами поверх пина).

РАЗВИЛКА, КОТОРУЮ НЕ РЕШАТЬ В ОДИНОЧКУ: (1) дописать пять расширений и четыре паттерна во встроенный список — дёшево, но следующий движок придёт снова; (2) дать конфиг-ручку rag.extra_extensions / rag.boundaries в .tausik/config.json, читаемую из rag_detect/rag_indexer, — лечит корень (асимметрию стеков и языков) и закрывает Unity/Unreal/самописные стеки заодно. Автор тикета склоняется ко (2). Цена (2) — валидация пользовательских регулярок и поведение при кривой ручке; тихо падать в None она права не имеет.

## Acceptance Criteria

## Plan

## Rollback

Правка аддитивна: новые записи в EXT_TO_LANG/_BOUNDARY_PATTERNS или новый необязательный блок rag.* в config.json. Откат — git revert; уже построенный индекс переиндексируется командой reindex, схема БД RAG не меняется.

## Journal
