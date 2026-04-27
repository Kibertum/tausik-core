[English](../en/doctor.md) | **Русский**

# Doctor — Health Check

`doctor` — единая команда, запускающая восемь проверок по разным частям TAUSIK-инсталляции (venv / DB / MCP / Skills / Drift / Config / Gates / Session). Она **не** автофиксит — говорит, что не так и как исправить.

## Запуск

```bash
.tausik/tausik doctor
```

Или через MCP: `tausik_doctor` (без параметров). MCP-вариант возвращает те же данные структурированным объектом.

## Что проверяется

| Группа | Проверка | Pass-критерий |
|-------|----------|---------------|
| **venv** | Python virtualenv | `.tausik/venv/` существует и `python -V` запускается |
| **venv** | stdlib only | Сторонние пакеты не утекли в venv |
| **DB** | SQLite файл | `.tausik/tausik.db` существует, открывается |
| **DB** | Schema migration | Применена последняя миграция (соответствует `backend_migrations.py`) |
| **DB** | FTS5 индексы | Все FTS-таблицы присутствуют и query'абельны |
| **MCP** | Project server | `.claude/mcp/project/server.py` существует |
| **MCP** | Brain server | `.claude/mcp/brain/server.py` существует |
| **MCP** | Server can start | `python server.py --probe` возвращает success |
| **Skills** | Deployment | Skills присутствуют в `.claude/skills/` (количество) |
| **Skills** | Critical skills | core skills `start`, `end`, `task`, `plan`, `review`, `brain`, `ship`, `checkpoint` все на месте |
| **Drift** | Bootstrap freshness | Файлы в `.claude/` соответствуют генераторам в `agents/`/`bootstrap/`. Drift = устаревшая сгенерированная копия. |
| **Config** | Knobs | `session_max_minutes`, `session_warn_threshold_minutes`, `session_idle_threshold_minutes`, `session_capacity_minutes`, `verify_cache_ttl_seconds` |
| **Gates** | Registered gates | Stack-detected + universal gates count |
| **Session** | Active vs wall | Если сессия открыта: `Xm active / Ym wall` (gap-based) |

## Пример вывода

```
TAUSIK doctor — health check
========================================
  OK    Python venv               .tausik/venv
  OK    Project DB                .tausik/tausik.db (3136 KB)
  OK    MCP server (project)      .claude/mcp/project/server.py
  OK    MCP server (brain)        .claude/mcp/brain/server.py
  OK    Core skills               38 deployed (all critical present)
  WARN  Bootstrap drift           1 script(s) differ — restart MCP server or re-bootstrap
  OK    Config knobs              max=180m warn=150m idle=10m capacity=200 cache_ttl=600s
  OK    Quality gates             6 registered
  OK    Session                   10m active / 10m wall
========================================
WARN OK with 1 warning(s).
```

## Уровни статуса

| Уровень | Значение |
|-------|---------|
| `OK` | Проверка прошла |
| `WARN` | Не блокирует — работа продолжается, но рекомендуется починить |
| `FAIL` | Блокирует — TAUSIK не работает корректно до починки |

Exit code отражает худший уровень: `0` для OK/WARN, `1` для FAIL.

## Типичные починки

| Симптом | Починка |
|---------|---------|
| `FAIL Python venv` | `python -m venv .tausik/venv` (или ребутстрэп) |
| `FAIL Project DB` | Запустите `.tausik/tausik init`, чтобы создать БД |
| `WARN Bootstrap drift` | `python .tausik-lib/bootstrap/bootstrap.py --refresh` и рестарт MCP-сервера |
| `FAIL MCP server` | Ребутстрэп; убедитесь, что `.claude/mcp/` сгенерирован |
| `WARN Core skills` | `tausik skill list`; `tausik skill activate <name>` для отсутствующих core skills |

## Negative — что Doctor НЕ делает

- **Не** автофиксит. Каждая строка показывает, что не так; команду fix запускаете вы.
- **Не** валидирует корректность vendor skill'ов — только наличие.
- **Не** тестирует синк brain mirror'а (используйте `tausik brain status`).
- **Не** запускает quality gates (используйте `tausik gates status` / `tausik verify`).

## См. также

- [CLI команды](cli.md) — полный справочник
- [Конфигурация](configuration.md) — knobs, которые проверяет doctor
- [Troubleshooting](troubleshooting.md) — глубокие шаги восстановления
