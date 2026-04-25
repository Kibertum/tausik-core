# CLAUDE.md

Инструкции для AI-агента в этом репозитории. Следуй им строго.

# TAUSIK — Технический Агент Унифицированного Сопровождения, Инспекции и Контроля

Кросс-IDE фреймворк для AI-агентов. Реализует [SENAR v1.3 Core](https://senar.tech) ([GitHub](https://github.com/Kibertum/SENAR)).
Управление задачами, сессиями, качеством, проектной памятью.

## Стек
Python 3.11+ (stdlib only) | Точка входа: `scripts/project.py`
БД: SQLite + FTS5 (`.tausik/tausik.db`) | venv: `.tausik/venv/` | Тесты: pytest (`tests/`)
Все данные в `.tausik/` — единственная директория для .gitignore.

## Принципы
TAUSIK — это фреймворк И его собственный пользователь (dogfooding).
- **Нулевая толерантность к тихим ошибкам.** Ошибка CLI? — создай баг-задачу.
- **Agent-first.** Перед закрытием задачи спроси: "поймёт ли свежий агент?"
- **Dogfooding.** Ты используешь этот фреймворк прямо сейчас. Неудобно — это баг.
- **SENAR ценности.** Контекст важнее кода. Верификация важнее скорости. Знания важнее опыта.

## Ограничения (жёсткие)

Quality gates (`tausik gates status`) контролируют автоматически.

- **Нет кода без задачи.** `task start` перед кодированием. Без исключений. (SENAR Rule 9.1)
- **QG-0 Context Gate.** `task start` требует goal + acceptance_criteria. Нет обходного пути — установи goal и AC перед началом.
- **QG-2 Implementation Gate.** `task done --ac-verified` требует evidence в notes + прохождения **scoped** quality gates. Pytest gate использует `{test_files_for_files}` substitution — гонит только `tests/test_<basename>.py` для каждого `relevant_files` (basename heuristic + glob `_*.py` варианты). Без `relevant_files` — fallback на полный suite. Verify cache (`verification_runs` table): зелёный run за последние 10 минут с тем же `files_hash` → cache hit, gate skipped. Security-sensitive файлы (`scripts/hooks/`, `/auth/`, `/payment/`, `/billing/`) обходят cache — всегда re-verify. Залогируй проверку AC через `task log` перед закрытием.
- **Нет коммита без gates.** Gates запускаются автоматически — исправь blocking failures.
- **Нет прямого доступа к БД.** Только MCP или CLI. Никакого raw SQLite.
- **Не угадывай аргументы CLI.** `tausik <cmd> --help` или `references/project-cli.md`.
- **Исходники в корне.** `scripts/`, `references/`, `agents/`, `bootstrap/` — не редактируй `.claude/` напрямую.
- **MCP-first.** MCP инструменты в приоритете; CLI как запасной вариант.
- **Git: спроси перед commit/push.** Всегда.
- **Макс. 400 строк на файл.** Filesize gate предупреждает. Исключения: тесты, сгенерированный код.
- **Непрерывное журналирование.** `task log <slug> "message"` после каждого шага. (SENAR Rule 9.4)
- **Документируй dead ends.** `.tausik/tausik dead-end "подход" "причина"` при неудаче. (SENAR Rule 9.4)
- **Checkpoint каждые 30-50 tool calls.** `/checkpoint` для сохранения, `/end` для завершения. (SENAR Rule 9.3)
- **Лимит сессии 180 мин.** `tausik status` предупреждает при превышении. (SENAR Rule 9.2)
- **Знания фреймворка остаются здесь.** Не сохраняй инструкции TAUSIK в auto-memory.

## Agent-native estimation

Задачи измеряются в **tool calls**, а не в часах. Шкала и бюджеты:

| Tier | call_budget | Когда подходит |
|------|-------------|----------------|
| `trivial` | ≤10 | мелкий fix, единственный флаг, doc-правка |
| `light` | ≤25 | миграция + helpers + тесты на одной поверхности |
| `moderate` | ≤60 | hook + service + tests, multi-file feature |
| `substantial` | ≤150 | CLI + service + MCP + mirror + tests одновременно |
| `deep` | ≤400 | полный вертикал (новый стэк, end-to-end feature) |

При создании task через `task add`/`task update` указывай `--call-budget` (авто-derives tier) или `--tier` напрямую. Пропуск допустим, но **явно** обоснуй — без budget calibration ломается. На task_done call_actual записывается автоматически (events + PostToolUse hook); если actual > 1.5×budget — TAUSIK логирует warning для re-calibration.

## Память

Два типа — используй правильный:

| Система | Где | Когда |
|---------|-----|-------|
| **TAUSIK memory** (`memory add`) | `.tausik/tausik.db` | Паттерны, dead ends, конвенции ЭТОГО проекта |
| **Claude auto-memory** (`~/.claude/`) | Домашний каталог | Предпочтения пользователя, кросс-проектные привычки |

Типы памяти: `pattern`, `gotcha`, `convention`, `context`, `dead_end`.
CLI: ВСЕГДА `.tausik/tausik <команда>`. НИКОГДА `python scripts/project.py` напрямую.

## Архитектура

Три слоя: **CLI → Service → Backend**. Подробности в `references/architecture.md`.

| Слой | Файлы | Назначение |
|------|-------|------------|
| CLI | `project.py`, `project_parser.py`, `project_cli.py`, `project_cli_extra.py`, `project_cli_ops.py` | argparse, диспетчеризация |
| Service | `project_service.py` + `service_task.py` + `service_knowledge.py` + `service_skills.py` + `service_gates.py` + `service_cascade.py` | Бизнес-логика, QG-0, QG-2, каскады |
| Backend | `project_backend.py` + `backend_crud.py` + `backend_schema.py` + `backend_migrations.py` + `backend_queries.py` | SQLite + FTS5, CRUD, метрики |
| Gates | `project_config.py` + `gate_runner.py` + `service_verification.py` | Quality gates конфигурация + scoped выполнение + verify cache |
| Batch | `plan_parser.py` | Парсер markdown-планов для `/run` |

**Граф workflow:** `start → plan → task → [review, test] → commit → end`
**Batch workflow:** `run plan.md → [task start → subagent → validate → commit] × N → summary`

## SENAR Compliance (v1.3 Core)

| Элемент SENAR | Реализация в TAUSIK | Enforcement |
|---|---|---|
| QG-0 Context Gate | `task start` проверяет goal + AC + negative scenario + scope warning | Hard (CLI + MCP блокирует) |
| QG-0 Security Surface | Предупреждает для auth/payment/PII задач без security AC | Warning |
| QG-2 Implementation Gate | `task done` = evidence + --ac-verified + **scoped** gates + verify cache (no bypass) | Hard (CLI + MCP, --force удалён) |
| Rule 1 Задача перед кодом | CLAUDE.md + skills + `/plan` для старта | Instruction |
| Rule 2 Scope Boundaries | Поля `scope` + `scope_exclude` в задачах, QG-0 предупреждает | Warning |
| Rule 3 Verify Against Criteria | Per-criterion AC evidence парсинг | Hard + Warning |
| Rule 5 Verification Checklist | 28-item checklist, 4 тира; **pytest gate scoped по relevant_files**, verify cache reuse в окне 10 мин | Warning + Hard scope |
| Rule 7 Root Cause | Defect-задачи предупреждают если нет root cause | Warning |
| Rule 8 Knowledge Capture | Warning при task_done + `--no-knowledge` для confirm-none | Warning |
| Rule 9.2 Лимит сессии | `task start` блокируется при >180 мин, `session extend` для продления | Hard (CLI + MCP блокирует) |
| Rule 9.3 Checkpoint | `/checkpoint` + auto-reminder в `/task` | Instruction |
| Rule 9.4 Dead Ends | `tausik_dead_end` MCP + CLI + skills напоминают | Instruction |
| Rule 9.5 Periodic Audit | `tausik_audit_check/mark` MCP + CLI | Warning |
| Rule 9.15 AI Output QA | `/review` с 5 параллельными агентами + iterative loop | Instruction |
| Метрика: Throughput | tasks_done / sessions | Hard (auto) |
| Метрика: Lead Time | avg(completed_at - created_at) | Hard (auto) |
| Метрика: FPSR | tasks(attempts=1) / done * 100% | Hard (auto) |
| Метрика: DER | DISTINCT(defect_of) / non-defect done * 100% | Hard (auto) |
| Метрика: Dead End Rate | dead_ends / total_tasks * 100% | Hard (auto) |
| Метрика: Cost per Task | avg hours by complexity | Hard (auto) |
| Section 5.1 Explorations | `tausik_explore_*` MCP + CLI | Hard |
| Multi-lang Gates | Auto-enable по стеку (TS, Go, Rust, PHP, Java) | Hard (auto) |
| MCP Coverage | 80 инструментов (73 project + 7 RAG), 0 CLI-only gaps | Hard |
| Batch Execution | `/run plan.md` — автономное выполнение планов | Instruction |
| Structured Logs | `task_logs` таблица с phase + FTS5 | Hard (auto) |
| Fake Test Detection | 10 паттернов в testing review agent | Warning |

## Команды

Полный справочник: `references/project-cli.md`. Быстрый старт: `references/QUICKSTART.md`.

```bash
.tausik/tausik status                        # обзор + предупреждения SENAR
.tausik/tausik task start <slug>             # активировать (QG-0: goal + AC)
.tausik/tausik task done <slug> --ac-verified # завершить (QG-2: evidence + scoped gates + cache)
.tausik/tausik verify --task <slug>          # ad-hoc scoped verify, записывает в verify cache
.tausik/tausik task log <slug> "message"     # журнал
.tausik/tausik metrics                       # SENAR метрики
.tausik/tausik dead-end "подход" "причина"   # документировать dead end
.tausik/tausik explore start "тема"          # начать exploration
.tausik/tausik audit check                   # проверить нужен ли аудит
.tausik/tausik task logs <slug>               # структурированные логи задачи
.tausik/tausik run plan.md                   # показать batch-план
.tausik/tausik search "<запрос>"             # FTS5 поиск
pytest tests/ -v                         # 918 тестов
```

**Статусы задач:** `planning → active → blocked | review → done`. Auto-cascade при завершении.
**Знания:** решение → `decide`. dead end → `dead-end`. паттерн → `memory add`. конец сессии → `session handoff`.

## Роли
Свободный текст (любая строка). Частые: `developer`, `architect`, `qa`, `tech-writer`. Профили в `agents/roles/{role}.md`.

## Внешние скиллы
Репозитории: `.tausik/tausik skill repo add <url>`. Установка: `.tausik/tausik skill install <name>`.
Активация: `.tausik/tausik skill activate {name}`. Деактивация: `.tausik/tausik skill deactivate {name}`.
Формат: `tausik-skills.json` в корне совместимого репо. Legacy: `skills.json` + bootstrap для обратной совместимости.

## Стеки
**DEFAULT_STACKS** (25): python, fastapi, django, flask, react, next, vue, nuxt, svelte, typescript, javascript, go, rust, java, kotlin, swift, flutter, laravel, php, blade, ansible, terraform, helm, kubernetes, docker.

**Custom stacks.** Список открыт для расширения — добавь свой стэк в `.tausik/config.json`:
```json
{ "custom_stacks": ["ruby", "elixir", "scala", "csharp"] }
```
После этого `task add --stack ruby` принимается. Stack-scoped gates (pytest, go-test и т.д.) автоматически НЕ применяются к custom стэкам — для них нужно зарегистрировать custom gate в `gates` секции config.json. Universal gates (filesize, tdd_order) работают для всех стэков. `tausik stack list` показывает custom стэки с пометкой `(custom)`.

Гайды в `agents/stacks/{stack}.md`.

<!-- DYNAMIC:START -->
## Current State
Session: none | Branch: main | Version: 1.3.0
Tasks: 0/1 done, 0 active, 0 blocked
<!-- DYNAMIC:END -->

Полная история изменений: `CHANGELOG.md`
