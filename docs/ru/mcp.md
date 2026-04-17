[English](../en/mcp.md) | **Русский**

# TAUSIK MCP — Справочник инструментов

82 инструмента для ИИ-агента (75 project + 7 RAG) начиная с v1.2.0. Используй MCP-инструменты вместо CLI-вызовов через bash.

## Статус и метрики

| Инструмент | Описание | Обязательные параметры |
|---|---|---|
| `tausik_health` | Проверка здоровья: версия, БД, таблицы | — |
| `tausik_status` | Обзор проекта: задачи, сессия, эпики | — |
| `tausik_metrics` | Метрики SENAR: производительность, доля успеха, уровень дефектов, доля тупиков, стоимость задачи | — |
| `tausik_search` | Полнотекстовый поиск по задачам, памяти, решениям | `query` |

## Задачи

| Инструмент | Описание | Обязательные параметры |
|---|---|---|
| `tausik_task_add` | Создать задачу (опционально в стори) | `slug`, `title` |
| `tausik_task_quick` | Быстрое создание с auto-slug | `title` |
| `tausik_task_start` | Начать работу (QG-0: требует goal + AC) | `slug` |
| `tausik_task_done` | Завершить (QG-2: `ac_verified=true`) | `slug` |
| `tausik_task_show` | Полная информация о задаче | `slug` |
| `tausik_task_list` | Список задач с фильтрами | — |
| `tausik_task_update` | Обновить поля (goal, AC, scope, notes) | `slug` |
| `tausik_task_plan` | Задать шаги плана | `slug`, `steps[]` |
| `tausik_task_step` | Отметить шаг выполненным | `slug`, `step_num` |
| `tausik_task_log` | Добавить запись в журнал | `slug`, `message` |
| `tausik_task_block` | Заблокировать задачу | `slug` |
| `tausik_task_unblock` | Разблокировать | `slug` |
| `tausik_task_review` | Перевести в review | `slug` |
| `tausik_task_delete` | Удалить задачу | `slug` |
| `tausik_task_move` | Переместить в другую стори | `slug`, `new_story_slug` |
| `tausik_task_next` | Подобрать следующую задачу | — |
| `tausik_task_claim` | Занять задачу (мульти-агент) | `slug`, `agent_id` |
| `tausik_task_unclaim` | Освободить задачу | `slug` |

### Параметры `tausik_task_add`
- `story_slug` — родительская стори (опционально)
- `goal` — цель задачи
- `role` — роль (свободный текст)
- `complexity` — `simple` / `medium` / `complex`
- `stack` — технологический стек
- `defect_of` — slug родительской задачи (для defect tracking)

### Параметры `tausik_task_update`
- `title`, `goal`, `notes`, `acceptance_criteria`, `scope`, `stack`, `complexity`, `role`

### Параметры `tausik_task_done`
- `ac_verified` — **обязательно** для QG-2 (подтверждение проверки AC)
- `no_knowledge` — подтвердить отсутствие знаний для захвата (подавляет предупреждение)
- `relevant_files[]` — файлы, изменённые в задаче

## Сессии

| Инструмент | Описание | Обязательные параметры |
|---|---|---|
| `tausik_session_start` | Начать сессию | — |
| `tausik_session_end` | Завершить сессию | — |
| `tausik_session_extend` | Продлить сессию сверх лимита 180 мин | — |
| `tausik_session_current` | Текущая активная сессия | — |
| `tausik_session_list` | Список сессий | — |
| `tausik_session_handoff` | Сохранить данные передачи | `handoff` (object) |
| `tausik_session_last_handoff` | Получить передачу предыдущей сессии | — |

## Иерархия (Эпики и Стори)

| Инструмент | Описание | Обязательные параметры |
|---|---|---|
| `tausik_epic_add` | Создать эпик | `slug`, `title` |
| `tausik_epic_list` | Список эпиков | — |
| `tausik_epic_done` | Завершить эпик | `slug` |
| `tausik_epic_delete` | Удалить (каскад: стори + задачи) | `slug` |
| `tausik_story_add` | Создать стори в эпике | `epic_slug`, `slug`, `title` |
| `tausik_story_list` | Список стори | — |
| `tausik_story_done` | Завершить стори | `slug` |
| `tausik_story_delete` | Удалить (каскад: задачи) | `slug` |
| `tausik_roadmap` | Дерево epic → story → task | — |

## Знания

| Инструмент | Описание | Обязательные параметры |
|---|---|---|
| `tausik_memory_add` | Сохранить в память проекта | `type`, `title`, `content` |
| `tausik_memory_search` | Полнотекстовый поиск по памяти | `query` |
| `tausik_memory_list` | Список записей (фильтр по типу) | — |
| `tausik_memory_show` | Показать запись по ID | `id` |
| `tausik_memory_delete` | Удалить запись | `id` |
| `tausik_memory_block` (v1.2) | Компактный markdown: decisions + conventions + dead ends для re-injection на /start | — |
| `tausik_memory_compact` (v1.2) | Агрегация recent task_logs (фазы + топ-слова + топ-файлы) — Dream-System-inspired | — |
| `tausik_decide` | Зафиксировать архитектурное решение | `decision` |
| `tausik_decisions_list` | Список решений | — |

Типы памяти: `pattern`, `gotcha`, `convention`, `context`, `dead_end`

## Графовая память

| Инструмент | Описание | Обязательные параметры |
|---|---|---|
| `tausik_memory_link` | Создать связь между узлами | `source_type`, `source_id`, `target_type`, `target_id`, `relation` |
| `tausik_memory_unlink` | Soft-invalidate связь | `edge_id` |
| `tausik_memory_related` | Найти связанные узлы (1-3 хопа) | `node_type`, `node_id` |
| `tausik_memory_graph` | Список связей с фильтрами | — |

Типы связей: `supersedes`, `caused_by`, `relates_to`, `contradicts`

## Dead Ends и Explorations

| Инструмент | Описание | Обязательные параметры |
|---|---|---|
| `tausik_dead_end` | Задокументировать неудачный подход | `approach`, `reason` |
| `tausik_explore_start` | Начать исследование (ограниченное по времени) | `title` |
| `tausik_explore_end` | Завершить исследование | — |
| `tausik_explore_current` | Текущее исследование | — |

## Шлюзы качества

| Инструмент | Описание | Обязательные параметры |
|---|---|---|
| `tausik_gates_status` | Статус всех шлюзов (по стекам) | — |
| `tausik_gates_enable` | Включить шлюз | `name` |
| `tausik_gates_disable` | Выключить шлюз | `name` |

Доступные шлюзы: `pytest`, `ruff`, `mypy`, `bandit`, `tsc`, `eslint`, `go-vet`, `golangci-lint`, `cargo-check`, `clippy`, `phpstan`, `phpcs`, `javac`, `ktlint`, `filesize`, `tdd_order`

> **`tdd_order`** (отключён по умолчанию) — TDD-контроль: проверяет, что тестовые файлы изменены вместе с исходным кодом. Включите через `tausik_gates_enable` с `name=tdd_order`.

## Навыки

| Инструмент | Описание | Обязательные параметры |
|---|---|---|
| `tausik_skill_list` | Список навыков: активные, установленные, доступные | — |
| `tausik_skill_install` | Установить навык из репо (copy + deps) | `name` |
| `tausik_skill_uninstall` | Удалить навык полностью | `name` |
| `tausik_skill_activate` | Активировать установленный навык | `name` |
| `tausik_skill_deactivate` | Деактивировать навык | `name` |
| `tausik_skill_repo_add` | Добавить TAUSIK-совместимый репозиторий | `url` |
| `tausik_skill_repo_remove` | Удалить репозиторий навыков | `name` |
| `tausik_skill_repo_list` | Список репозиториев и доступных навыков | — |

## Аудит и обслуживание

| Инструмент | Описание | Обязательные параметры |
|---|---|---|
| `tausik_audit_check` | Проверить нужен ли аудит (SENAR Rule 9.5) | — |
| `tausik_audit_mark` | Отметить аудит проведённым | — |
| `tausik_events` | Журнал аудита (события) | — |
| `tausik_update_claudemd` | Обновить dynamic-секцию CLAUDE.md | — |
| `tausik_fts_optimize` | Оптимизировать FTS5 индексы | — |
| `tausik_health` | Проверка здоровья сервера | — |
| `tausik_team` | Задачи по агентам | — |

## Поиск по кодовой базе (отдельный MCP-сервер)

| Инструмент | Описание | Обязательные параметры |
|---|---|---|
| `search_code` | Поиск по коду проекта через RAG-индекс | `query` |
| `search_knowledge` | Поиск по базе знаний проекта | `query` |
| `reindex` | Переиндексировать кодовую базу | — |
| `rag_status` | Статус RAG-индекса (размер, дата) | — |
| `archive_done` | Архивировать завершённые задачи | — |
| `cache_web_result` | Кешировать результат веб-поиска (экономит токены) | `query`, `content` |
| `search_web_cache` | Поиск по кешу веб-результатов | `query` |
