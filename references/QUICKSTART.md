# TAUSIK — Быстрый старт для AI-агентов

[English](QUICKSTART.en.md) | **Русский**

Эта инструкция для AI-агента (Claude Code, Cursor, Windsurf), который впервые подключается к проекту с TAUSIK.
TAUSIK (**Т**ехнический **А**гент **У**нифицированного **С**опровождения, **И**нспекции и **К**онтроля) реализует [SENAR v1.3 Core](https://senar.tech) ([spec](https://github.com/Kibertum/SENAR)).

См. также: [AGENTS.md](../AGENTS.md) — обзор правил и онбординг.
Полная документация для людей: [docs/](../docs/README.md)

## Требования

**Python >= 3.11** должен быть доступен в PATH. Bootstrap автоматически:
1. Найдёт подходящий Python (venv > python3 > python > py -3 на Windows)
2. Создаст изолированное окружение `.tausik/venv/`
3. Установит зависимости (`mcp` и др.) в venv
4. Настроит MCP-серверы на использование venv Python

Если Python не найден, bootstrap покажет инструкцию по установке для каждой платформы.

## Установка

```bash
git submodule add https://github.com/Kibertum/tausik-core .tausik-lib
python .tausik-lib/bootstrap/bootstrap.py --smart --init my-project
echo ".tausik/" >> .gitignore
```

> После bootstrap **перезапустите окно IDE**, чтобы MCP-серверы загрузились.

## Рабочий цикл (MCP-first)

Предпочитай MCP-инструменты (`tausik_task_start`, `tausik_status`) вместо CLI bash.

### Быстрый путь

```
Пользователь: "начинай работу"     → /start (сессия + контекст)
Пользователь: "исправь баг с JWT"  → /plan (создаёт задачу + стартует)
Пользователь: "готово"             → /ship (review + gates + commit)
```

### Полный путь

```
/start    → tausik_session_start, tausik_status, tausik_session_last_handoff
/plan     → tausik_task_quick или tausik_task_add + tausik_task_update (AC)
/task     → tausik_task_start (QG-0) → работа → tausik_task_log → tausik_task_step
/task done → tausik_task_done (QG-2: ac_verified=true)
/review   → 28-item SENAR checklist
/commit   → git commit с gates
/end      → tausik_session_end + tausik_session_handoff
```

## Quality Gates

| Gate | Когда | Что проверяет |
|------|-------|---------------|
| QG-0 | `tausik_task_start` | goal + AC заполнены |
| QG-2 | `tausik_task_done` | AC verified + gates (pytest, ruff) |

## Ключевые MCP-инструменты

Полный справочник: [docs/ru/mcp.md](../docs/ru/mcp.md)

```
tausik_status              — обзор проекта
tausik_task_quick          — быстрое создание задачи
tausik_task_start          — начать (QG-0)
tausik_task_done           — завершить (QG-2, ac_verified=true)
tausik_task_log            — журнал прогресса
tausik_dead_end            — документировать неудачу
tausik_memory_search       — поиск по памяти
tausik_explore_start/end   — исследование
tausik_metrics             — SENAR метрики
```

## Что нельзя

- Код без задачи — `/plan` → `/task`
- Закрыть задачу без AC evidence — `tausik_task_log` + `ac_verified=true`
- Работать >180 минут без `/checkpoint`
- Коммитить без подтверждения пользователя
- Обращаться к БД напрямую — только MCP или CLI
