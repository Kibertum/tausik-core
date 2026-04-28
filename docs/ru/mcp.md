[English](../en/mcp.md) | **Русский**

# TAUSIK MCP — Справочник инструментов (v1.3)

**96 инструментов** для ИИ-агентов (90 project + 6 brain). MCP-surface зеркалит CLI 1:1 без CLI-only пробелов. Предпочитайте MCP-инструменты shell-вызовам — они атомарны, возвращают структурированные данные и держат контекст чище.

В проекте живут два MCP-сервера:

- `tausik-project` — project-scoped инструменты (90): tasks, sessions, knowledge, stacks, roles, gates, skills, exploration, audit, doctor, verify.
- `tausik-brain` — cross-project Shared Brain инструменты (6).

Опционально доступен `codebase-rag` сервер (документирован в конце).

## Status, Health, Metrics

| Инструмент | Описание | Обязательные параметры |
|---|---|---|
| `tausik_health` | Health check: версия, DB, таблицы | — |
| `tausik_status` | Обзор проекта: задачи, сессия, эпики | — |
| `tausik_doctor` | 4-group health (venv + DB + MCP + skills + drift) | — |
| `tausik_metrics` | Метрики SENAR: Throughput, FPSR, DER, Dead End Rate, Cost/Task | — |
| `tausik_search` | Полнотекстовый поиск по задачам, памяти, решениям | `query` |

## Задачи

| Инструмент | Описание | Обязательные параметры |
|---|---|---|
| `tausik_task_add` | Создать задачу (опционально в стори) | `slug`, `title` |
| `tausik_task_quick` | Быстрое создание с auto-slug | `title` |
| `tausik_task_start` | Начать работу (QG-0: требует goal + AC + negative scenario) | `slug` |
| `tausik_task_done` | Завершить (QG-2: `ac_verified=true`, scoped pytest, verify cache) | `slug` |
| `tausik_task_show` | Полная информация | `slug` |
| `tausik_task_list` | Список с фильтрами (status enum: `planning,active,blocked,review,done`) | — |
| `tausik_task_update` | Обновить поля (title/goal/AC/scope/notes/stack/complexity/role/tier/call_budget) | `slug` |
| `tausik_task_plan` | Задать шаги плана | `slug`, `steps[]` |
| `tausik_task_step` | Отметить шаг выполненным | `slug`, `step_num` |
| `tausik_task_log` | Добавить запись в журнал | `slug`, `message` |
| `tausik_task_logs` | Чтение структурированных логов (фильтр по фазе) | `slug` |
| `tausik_task_block` | Заблокировать | `slug` |
| `tausik_task_unblock` | Разблокировать | `slug` |
| `tausik_task_review` | Перевести в review | `slug` |
| `tausik_task_delete` | Удалить | `slug` |
| `tausik_task_move` | Переместить в другую стори | `slug`, `new_story_slug` |
| `tausik_task_next` | Выбрать следующую задачу по score | — |
| `tausik_task_claim` | Занять задачу (мульти-агент) | `slug`, `agent_id` |
| `tausik_task_unclaim` | Освободить | `slug` |

### `tausik_task_done` параметры

- `ac_verified` — **обязательно** для QG-2
- `evidence` — inline AC verification log (заменяет отдельный `task_log` вызов)
- `no_knowledge` — подтвердить отсутствие знаний для фиксации (подавляет warning)
- `relevant_files[]` — изменённые файлы; драйвят **scoped** pytest gate (basename match → `tests/test_<file>.py`). Empty list при non-empty original → gate skipped (нет ложных срабатываний на full suite). Verify cache (10 min TTL) пропускает re-run при том же `files_hash`.

`task_done` **не имеет `--force`** — QG-2 нельзя байпаснуть. У `task_start` `--force` есть для байпаса session capacity, с audit trail.

## Сессии

| Инструмент | Описание | Обязательные параметры |
|---|---|---|
| `tausik_session_start` | Начать сессию | — |
| `tausik_session_end` | Завершить сессию | — |
| `tausik_session_extend` | Продлить active-time лимит сверх 180 мин | — |
| `tausik_session_current` | Текущая активная сессия | — |
| `tausik_session_list` | Список сессий | — |
| `tausik_session_handoff` | Сохранить handoff data | `handoff` (object) |
| `tausik_session_last_handoff` | Получить handoff из предыдущей сессии | — |

Лимит сессии — gap-based **active time** (паузится после 10-min idle gap), не wall clock. См. `session-active-time.md`.

## Иерархия (эпики и стори)

| Инструмент | Описание | Обязательные параметры |
|---|---|---|
| `tausik_epic_add` | Создать эпик | `slug`, `title` |
| `tausik_epic_list` | Список эпиков | — |
| `tausik_epic_done` | Завершить эпик | `slug` |
| `tausik_epic_delete` | Удалить (cascade: стори + задачи) | `slug` |
| `tausik_story_add` | Создать стори в эпике | `epic_slug`, `slug`, `title` |
| `tausik_story_list` | Список стори | — |
| `tausik_story_done` | Завершить стори | `slug` |
| `tausik_story_delete` | Удалить (cascade: задачи) | `slug` |
| `tausik_roadmap` | Дерево: epic → story → task | — |

## Знания

| Инструмент | Описание | Обязательные параметры |
|---|---|---|
| `tausik_memory_add` | Сохранить в проектную память | `type`, `title`, `content` |
| `tausik_memory_search` | Полнотекстовый поиск | `query` |
| `tausik_memory_list` | Список (фильтр по типу) | — |
| `tausik_memory_show` | Показать запись по ID | `id` |
| `tausik_memory_delete` | Удалить запись | `id` |
| `tausik_memory_block` | Compact markdown: recent decisions + conventions + dead ends (для /start re-injection) | — |
| `tausik_memory_compact` | Aggregate recent task_logs (phases + top words + top files) | — |
| `tausik_decide` | Записать архитектурное решение | `decision` |
| `tausik_decisions_list` | Список решений | — |

Типы памяти: `pattern`, `gotcha`, `convention`, `context`, `dead_end`.

## Графовая память

| Инструмент | Описание | Обязательные параметры |
|---|---|---|
| `tausik_memory_link` | Создать связь между узлами | `source_type`, `source_id`, `target_type`, `target_id`, `relation` |
| `tausik_memory_unlink` | Soft-invalidate связь (никогда не удаляет) | `edge_id` |
| `tausik_memory_related` | Найти связанные узлы (1–3 hops) | `node_type`, `node_id` |
| `tausik_memory_graph` | Список связей с фильтрами | — |

Типы связей: `supersedes`, `caused_by`, `relates_to`, `contradicts`.

## Тупики и исследования

| Инструмент | Описание | Обязательные параметры |
|---|---|---|
| `tausik_dead_end` | Документировать неудачный подход | `approach`, `reason` |
| `tausik_explore_start` | Начать time-boxed исследование | `title` |
| `tausik_explore_end` | Завершить исследование | — |
| `tausik_explore_current` | Текущее исследование | — |

## Шлюзы качества и верификация

| Инструмент | Описание | Обязательные параметры |
|---|---|---|
| `tausik_gates_status` | Статус всех gates (по стеку) | — |
| `tausik_gates_enable` | Включить gate | `name` |
| `tausik_gates_disable` | Выключить gate | `name` |
| `tausik_verify` | Запустить scoped quality gates ad-hoc; пишет в verify cache | — (`task` + `scope` опционально) |

Доступные gates: `pytest`, `ruff`, `mypy`, `bandit`, `tsc`, `eslint`, `go-vet`, `golangci-lint`, `cargo-check`, `clippy`, `phpstan`, `phpcs`, `javac`, `ktlint`, `filesize`, `tdd_order`. Stack-scoped gates авто-включаются по обнаруженному стеку; universal gates (`filesize`, `tdd_order`) применяются ко всем стекам.

`tdd_order` отключён по умолчанию. Включите через `tausik_gates_enable name=tdd_order`.

## Стеки

| Инструмент | Описание | Обязательные параметры |
|---|---|---|
| `tausik_stack_list` | Список встроенных + custom стеков | — |
| `tausik_stack_show` | Резолвленный стек: gates per language + override info | `stack` |
| `tausik_stack_export` | Экспорт резолвленной декларации как JSON | `stack` |
| `tausik_stack_diff` | Diff между built-in и user override | `stack` |
| `tausik_stack_reset` | Удалить user override в `.tausik/stacks/<stack>/` | `stack` |
| `tausik_stack_lint` | Валидировать user-override `stack.json` | — |
| `tausik_stack_scaffold` | Создать `.tausik/stacks/<name>/{stack.json,guide.md}` skeleton | `name` |

DEFAULT_STACKS: 25 записей (python, fastapi, django, flask, react, next, vue, nuxt, svelte, typescript, javascript, go, rust, java, kotlin, swift, flutter, laravel, php, blade, ansible, terraform, helm, kubernetes, docker). Custom-стеки через `.tausik/config.json` → `custom_stacks`.

## Роли

| Инструмент | Описание | Обязательные параметры |
|---|---|---|
| `tausik_role_list` | Список ролей | — |
| `tausik_role_show` | Профиль роли | `slug` |
| `tausik_role_create` | Создать роль (опционально `extends` базовый профиль) | `slug`, `title` |
| `tausik_role_update` | Обновить метаданные | `slug` |
| `tausik_role_delete` | Удалить роль | `slug` |
| `tausik_role_seed` | Bootstrap из `agents/roles/*.md` + использования в задачах | — |

Хранение ролей гибридное: SQLite-метаданные + markdown-профиль `agents/roles/{role}.md`. Роли в задачах остаются свободным текстом.

## Периодический аудит (SENAR Rule 9.5)

| Инструмент | Описание | Обязательные параметры |
|---|---|---|
| `tausik_audit_check` | Просрочен ли аудит | — |
| `tausik_audit_mark` | Отметить аудит выполненным | — |

## Навыки

| Инструмент | Описание | Обязательные параметры |
|---|---|---|
| `tausik_skill_list` | Список навыков: активные, vendored, доступные | — |
| `tausik_skill_install` | Установить из репо (clone + copy + deps) | `name` |
| `tausik_skill_uninstall` | Удалить полностью | `name` |
| `tausik_skill_activate` | Активировать установленный | `name` |
| `tausik_skill_deactivate` | Деактивировать (файлы остаются) | `name` |
| `tausik_skill_repo_add` | Добавить TAUSIK-совместимый репо | `url` |
| `tausik_skill_repo_remove` | Удалить репо | `name` |
| `tausik_skill_repo_list` | Список репозиториев и доступных skills | — |

## Cross-Project Queue (CQ)

| Инструмент | Описание | Обязательные параметры |
|---|---|---|
| `tausik_cq_publish` | Опубликовать cross-project event | `payload` |
| `tausik_cq_query` | Query cross-project queue | — |

## Мульти-агент и обслуживание

| Инструмент | Описание | Обязательные параметры |
|---|---|---|
| `tausik_team` | Задачи сгруппированные по агентам | — |
| `tausik_events` | Audit log (events) | — |
| `tausik_update_claudemd` | Обновить динамическую секцию в CLAUDE.md | — |
| `tausik_fts_optimize` | Оптимизировать FTS5 индексы | — |

## Shared Brain (`tausik-brain`, 6 инструментов)

| Инструмент | Описание | Обязательные параметры |
|---|---|---|
| `brain_search` | Поиск в Notion-backed brain (FTS по local mirror) | `query` |
| `brain_get` | Получить brain-запись по id | `id` |
| `brain_store_decision` | Сохранить cross-project решение | `title`, `body` |
| `brain_store_pattern` | Сохранить cross-project паттерн | `title`, `body` |
| `brain_store_gotcha` | Сохранить cross-project gotcha | `title`, `body` |
| `brain_cache_web` | Кешировать web-результат для token reuse | `query`, `content` |

`tausik-brain` MCP-сервер запускается config-agnostic и читает реестр из `.tausik-brain/` конфигурации. Экспонирует дополнительные внутренние инструменты (registry, mirror sync), доводя счётчик brain до 6.

## Codebase RAG (отдельный опциональный MCP-сервер)

| Инструмент | Описание | Обязательные параметры |
|---|---|---|
| `search_code` | Поиск кода через RAG-индекс | `query` |
| `search_knowledge` | Поиск в knowledge base | `query` |
| `reindex` | Реиндексация кодбазы | — |
| `rag_status` | Статус RAG-индекса | — |
| `archive_done` | Архивировать выполненные задачи | — |
| `cache_web_result` | Кешировать web-результат | `query`, `content` |
| `search_web_cache` | Поиск кешированных web-результатов | `query` |

Эти не входят в счёт 96+10 — принадлежат опциональному `codebase-rag` серверу.

## Запуск Tausik MCP-сервера

Bootstrap-шаг генерирует IDE-specific MCP-launchers под `agents/<ide>/mcp/`. Claude Code читает `.claude/settings.json` (auto-generated). Для регенерации запустите `python .tausik-lib/bootstrap/bootstrap.py --refresh`.
