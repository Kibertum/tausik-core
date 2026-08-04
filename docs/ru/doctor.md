[English](/docs/doctor) | **Русский**

# Doctor — Health Check

`doctor` — единая команда, проверяющая подвижные части TAUSIK-инсталляции: venv, БД, MCP-серверы, скиллы, дрейф развёртывания, конфиг, гейты, сессию и гигиену бэклога. Она **не** автофиксит — говорит, что не так и как исправить.

Часть проверок выполняется, только если проверяемое установлено (конфиги Kilo и OpenCode, Brain), поэтому число строк в выводе зависит от вашей раскладки. В таблице ниже перечислены все проверки, которые могут появиться.

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
| **Skills** | Critical skills | core skills `start`, `end`, `task`, `plan`, `checkpoint`, `commit`, `explore`, `review`, `test`, `ship`, `debug` все на месте (плюс `/brain` опционально, если настроен Notion) |
| **Drift** | Bootstrap freshness | Файлы в `.claude/` соответствуют генераторам в `harness/`/`bootstrap/`. Drift = устаревшая сгенерированная копия. |
| **Config** | Knobs | `session_max_minutes`, `session_warn_threshold_minutes`, `session_idle_threshold_minutes`, `session_capacity_calls`, `verify_cache_ttl_seconds` |
| **Gates** | Registered gates | Stack-detected + universal gates count |
| **Session** | Active vs wall | Если сессия открыта: `Xm active / Ym wall` (gap-based) |
| **Backlog** | Epic reachability | Каждая открытая задача (planning/active/blocked/review) достижима из эпика. Задача без story не видна ни `tausik roadmap`, ни `task list --epic` — то есть выпадает из подсчёта объёма релиза молча. WARN, не FAIL: standalone-задача законна. Закрытые задачи не считаются. |
| **Backlog** | Deferred AC | Ни одна закрытая задача внутри **ещё открытого** эпика не оставила критерий приёмки с пометкой `DEFERRED`. У такого критерия нет ни владельца, ни срока, а эпик может закрыться поверх него. Гасится либо выполнением критерия, либо передачей его задаче-владельцу с записью об этом: `tausik task log <slug> "AC-N CARRIED BY <owning-slug>"`. Область намеренно сужена до открытых эпиков — критерий, отложенный в давно отгруженном эпике, это история, а не работа. |
| **Drift** | CLAUDE.md drift | Секции, которые ваш `CLAUDE.md` несёт под **собственным** заголовком шаблона, всё ещё совпадают с шаблоном. Заголовок, которого в файле нет, — это кастомизация, а не дрейф: перевести, переименовать или убрать секцию есть намеренный выбор. Отсутствие секции всё же считается дрейфом, когда файл в остальном *и есть* документ шаблона (больше половины секций на месте), — так что проект, чей конфиг требует директиву, которой в `CLAUDE.md` нет, ловится как и раньше. Ремедиация называет разошедшиеся секции и никогда не советует перезапустить bootstrap, который затёр бы написанное вручную. |
| **Config** | Trust tier | Ни один ключ конфига проектного уровня не ослабляет enforcement. См. [config-trust-tiers.md](config-trust-tiers.md). |
| **Config** | Verify-First profile | `auto_verify` не включается молча на интерактивной машине. |
| **IDE** | Kilo / OpenCode config | Появляется, только если профиль этой IDE установлен: конфиг разбирается и его MCP-секция `tausik-project` резолвится. |
| **Brain** | Notion config | Появляется, только если Brain включён: заданы все четыре `database_ids` и токен. |

## Пример вывода

```
TAUSIK doctor — health check
========================================
  OK    Python venv               .tausik/venv
  OK    Project DB                .tausik/tausik.db (3136 KB)
  OK    MCP server (project)      .claude/mcp/project/server.py
  OK    MCP server (brain)        .claude/mcp/brain/server.py
  OK    Core skills               12 core + brain conditional, 20 vendor opt-in (all critical present)
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
| `WARN Shared Brain` | Появляется только когда `.tausik/config.json` не удалось истолковать — испорченный файл либо ключ `brain`, который не является словарём (`{"brain": true}`). Brain считается ВЫКЛЮЧЕННЫМ, как и по умолчанию, поэтому проверка от этого не падает. Почините конфиг, если Notion-brain вам нужен; игнорируйте, если нет. |
| `WARN Backlog hygiene` | `tausik task move <slug> <story>` для каждой названной задачи — либо создайте story под них, если они образуют связную группу |

## Negative — что Doctor НЕ делает

- **Не** автофиксит. Каждая строка показывает, что не так; команду fix запускаете вы.
- **Не** валидирует корректность vendor skill'ов — только наличие.
- **Не** тестирует синк brain mirror'а (используйте `tausik brain status`).
- **Не** запускает quality gates (используйте `tausik gates status` / `tausik verify`).

## См. также

- [CLI команды](cli.md) — полный справочник
- [Конфигурация](configuration.md) — knobs, которые проверяет doctor
- [Troubleshooting](troubleshooting.md) — глубокие шаги восстановления
