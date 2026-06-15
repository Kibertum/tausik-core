[English](/docs/troubleshooting) | **Русский**

# Troubleshooting

> Машино-читаемый гайд: ошибка → диагноз → фикс.

## Stale MCP-модули (тихие зависания)

Симптом: `tausik_verify` или `tausik_task_done` не возвращаются. CLI той же операции работает мгновенно. MCP-сервер исполняет stale Python-модули — обычно потому, что код service-слоя редактировался ПОСЛЕ старта IDE, а MCP-дочерний процесс не перезапустился. Несколько MCP project-серверов для одного проекта — тоже жёсткий признак (каждое прошлое IDE-окно оставляет один процесс).

| Симптом | Диагноз | Фикс |
|---|---|---|
| MCP-инструмент висит > 60 с, тот же flow через CLI отрабатывает мгновенно | `tausik_self_check` скорее всего показывает `drift_detected=true` или `sibling_mcp_count > 0` — старые модули в памяти | Перезапусти IDE, чтобы MCP project-сервер пересоздался. Пока что — `.tausik/tausik` CLI. |
| `/start` предупреждает `⚠ MCP Health` со списком stale-модулей | mtime watched-модуля стал больше времени старта MCP | Перезапусти IDE; повтори `/start`. |
| `sibling_mcp_count > 0` | Несколько MCP project-серверов на одном проекте (window leak) | Закрой stale IDE-окна, затем `Get-Process python` (Windows) / `pgrep -f mcp/project/server.py` (POSIX), убей старые PID'ы. |
| `tausik_self_check` возвращает `error: self_check unavailable` | Запущенный MCP-сервер старше этой диагностики (предшествует v1.4 polish) | Перезапусти IDE — на новом старте инструмент уже зарегистрируется. |

Сопутствующие gotchas в `.tausik/tausik.db`: #77 (verify висит после правки `service_verification.py`/`gate_runner.py`), #79 (`task_done` виснет на большом evidence), #80 (root cause = stale-модули + параллельные MCP-серверы). Envelope timeout (60 с, `verify_pipeline_timeout_seconds`) Verify-First Contract'а ловит новые серверы; старые загрузили свой код ДО появления envelope и игнорируют его.

## Failed verify-gate → tausik-gate-fixer (auto-helper)

Когда `tausik verify` или `tausik task done` падает с blocking-failure (filesize / ruff / mypy / pytest), вместо ручного парсинга stderr вызови sub-agent **`tausik-gate-fixer`** — он читает stderr + `docs/en/troubleshooting.md` + `docs/en/architecture.md` и возвращает 1-3 шаговый JSON fix plan.

```
Agent(
  subagent_type="tausik-gate-fixer",
  prompt="gate_name=ruff; stderr=<copied>; relevant_files=[...]; task_slug=<slug>; goal=<task goal>",
)
```

Ответ:
```json
{"gate":"ruff","family":"style","plan":[{"step":1,"action":"edit","target":"scripts/foo.py:42","change":"...","why":"..."}],"meta":{...}}
```

**Action vocabulary** (фиксированный, агент не выдумывает): `edit`, `extract_module`, `add_test`, `move_file`, `delete_dead_code`, `re_run_gate`. Применяешь plan — потом `.tausik/tausik verify --task <slug>` ещё раз. Sub-agent read-only: никогда не правит код сам.

## Bootstrap

| Симптом | Диагноз | Фикс |
|---|---|---|
| `python: command not found` | Python не в PATH | Установи Python 3.11+, проверь `python --version` |
| `Bootstrap halts on .claude/ write` | Read-only FS | Mount `.tausik/` writable; bootstrap пишет и в `.claude/` |
| Bootstrap "Skills: 0 copied" | `harness/skills/` пуст | Pull актуальный source, проверь `ls harness/skills/` |
| Bootstrap занимает >60s на Windows | Antivirus сканирует каждый файл | Исключи `.claude/` и `.tausik/` из real-time scan |

## CLI / MCP

| Симптом | Диагноз | Фикс |
|---|---|---|
| `tausik_task_done` зависает / таймаут в VS Code Claude Extension | Тяжёлые гейты (pytest, tsc) шли inline, хост убил вызов на per-tool таймауте | v1.4 Verify-First Contract: сначала `tausik_verify` (стримит прогресс, можно прервать), затем `tausik_task_done` читает кеш и закрывает за миллисекунды. См. [Лимиты хоста](#лимиты-хоста-task_done-ux). |
| `tausik_task_done` возвращает generic timeout без traceback | Старый MCP-сервер (до 1.4) проглатывал исключения в одну строку | Обнови MCP-сервер: `python bootstrap/bootstrap.py` (1.4 пишет traceback в stderr). |
| Агент запускает тяжёлые гейты inline при закрытии задачи | MCP-сервер в проекте предшествует 1.4 (Verify-First Contract) | Обнови bootstrap: `python bootstrap/bootstrap.py`. В 1.4 verify отделён от close — `tausik_verify` стримит прогресс, `tausik_task_done` читает кеш. |
| MCP tool returns stale data | MCP server cached старые scripts/* модули | Restart IDE session (re-bootstrap не помогает) |
| `tausik doctor` reports drift | Source `scripts/` отличается от `.claude/scripts/` | Re-run `python bootstrap/bootstrap.py --ide claude` |
| `Memory #N not found` | Не указано в какой DB | Сейчас всегда project DB; brain — отдельная команда `tausik brain show` |

## Лимиты хоста & `task_done` UX

MCP-серверы TAUSIK работают внутри IDE-хоста (VS Code Claude Extension, JetBrains, Cursor, Claude Code и т.д.). Каждый хост применяет per-tool таймаут (~60с в текущих сборках). Если `task_done` запускал тяжёлый стек проверок inline, большие monorepo выходили за таймаут, хост убивал вызов, и агент видел generic transport error — а не полезный отчёт об ошибке.

**Workflow (предпочитаемый):**
1. `tausik_verify(task_slug=…)` — запускает тяжёлые гейты (pytest, tsc, cargo, phpstan, …), стримит прогресс, пользователь может корректно прервать. Результат кешируется на 10 минут.
2. `tausik_task_done(slug=…, ac_verified=True, relevant_files=[…])` — читает кеш, закрывает задачу за миллисекунды. Возвращает structured JSON (`stage`, `gate_results`, `blocking_failures`).

**Opt-out (CI / batch):** добавь `{ "task_done": { "auto_verify": true } }` в `.tausik/config.json`. `task_done` будет запускать тяжёлые гейты inline как в 1.3 — это нормально вне интерактивного хоста, где нет per-tool таймаута.

**`tausik_task_done` — единая QG-2 entrypoint.** В предыдущих доках упоминалась миграция `task_done_v2 vs task_done`; v1.4 публикует только один `tausik_task_done` (structured JSON: `stage`, `gate_results`, `blocking_failures`). Соблюдает Verify-First Contract — тяжёлые гейты должны быть уже прогнаны через `tausik_verify`, результат кешируется на 10 минут, `task_done` читает этот кеш.

**Streaming-прогресс (v1.4):** когда `task done` запускает гейты inline (`auto_verify=true` или интерактивный `tausik task done`), `gate_runner` шлёт событие `run_start` ДО первого гейта с `total` (количество гейтов) и `max_seconds` (сумма таймаутов), чтобы MCP-хост показал ETA до того, как pytest заблокирует канал. CLI-обработчик мапит каждое событие в одну stderr-строку:

```
[gates] Running 2 gate(s) (trigger=task-done, max ~125s).
[gates] 1/2 filesize ...
[gates] 1/2 filesize PASS (8 ms)
[gates] 2/2 pytest ...
[gates] 2/2 pytest PASS (1062 ms)
```

`TAUSIK_QUIET=1` глушит вывод (CI / скриптовые прогоны). MCP-серверы получают тот же payload и могут отрендерить структурированное progress-сообщение.

## VS Code Claude Extension — полный справочник (v1.4)

VS Code Claude Extension — самый строгий MCP-хост для TAUSIK потому что (1) у него жёсткий per-tool таймаут, который нельзя поменять изнутри инструмента, (2) нет hooks API, (3) рендерит результат MCP-tool как одну строку. v1.4 настроена под этот хост явно. Эта секция консолидирует полный список нюансов.

### Статус хуков

| Категория хуков | Claude Code (CLI) | Cursor | VS Code Claude Ext. | Qwen Code |
|---|---|---|---|---|
| PreToolUse / PostToolUse / SessionStart / SessionEnd | ✅ Реальные, enforced | ❌ Нет hooks API | ❌ Нет hooks API | ✅ Реальные, enforced (полный паритет с v1.4) |
| `task_gate.py` (Rule 9.1) | Hard block | Только инструкция | Только инструкция | Hard block |
| `secret_scan.py` (Rule 10.12) | Warn / strict-block | Только инструкция | Только инструкция | Warn / strict-block |
| `git_push_gate.py` | Hard block | Только инструкция | Только инструкция | Hard block |

Практический вывод: VS Code extension не может заблокировать запись файла, когда нет активной задачи TAUSIK. Агент *должен* соблюдать правило (оно явно прописано в `CLAUDE.md` и multi-model onboarding-блоке `AGENTS.md`), но safety net отсутствует. В этом хосте правила — это конвенция, не gate.

### Per-tool таймаут MCP

Текущая сборка extension убивает любой MCP-вызов длиннее ~60 секунд. Клиентского переключателя нет. Затронутые tools и v1.4 mitigation:

| Tool | До 1.4 | Mitigation в 1.4 |
|---|---|---|
| `tausik_task_done` | Запускал pytest/tsc/cargo inline → 60с+ на большом repo → kill → generic timeout | **Verify-First Contract**: отказывается закрывать пока не отработал `tausik_verify`. Verify пишет stderr прогресс, юзер может прервать, результат кешируется на 10 мин. Затем `task done` читает кеш и закрывает за <100мс. Возвращает structured JSON (`stage`, `gate_results`, `blocking_failures`) вместо одной строки ошибки. |
| `codebase-rag.reindex` (full) | Молча обходил все файлы → kill на 60с | Принимает `max_seconds` soft-limit; пишет `[rag] indexed X/Y files...` в stderr каждые 100 файлов. По умолчанию `incremental` — только файлы изменённые с `last_commit`. |
| `tausik_verify` | (введён в 1.4) | Намеренная foreground-точка для тяжёлой работы. Стримит прогресс; юзер видит что происходит; хост не таймаутит пока мы пишем байты в свой idle-порог. |

### Рекомендованный workflow

Для рутинного закрытия задачи в VS Code Claude Extension:

1. Скилл/агент сначала зовёт `tausik_verify(task_slug=...)`. Это единственное место, где pytest/tsc/etc. разрешено запускать inline.
2. Юзер видит streaming-прогресс и может вмешаться (Ctrl-C доходит до MCP-процесса).
3. На зелёном `tausik_verify` пишет строку в `verification_runs`.
4. Скилл зовёт `tausik_task_done(task_slug=..., relevant_files=[...], ac_verified=true)`.
5. `task_done` проверяет кеш (≤10 мин, тот же `files_hash`, та же gate signature), убеждается в зелёном статусе и закрывает задачу за ~100мс.
6. Если в кеше промах — `task_done` возвращает структурированную ошибку с указанием конкретного отсутствующего gate, **не** transport timeout.

Для CI / batch / non-interactive прогонов (где нет per-tool таймаута), поставь `{ "task_done": { "auto_verify": true } }` в `.tausik/config.json` чтобы вернуть legacy 1.3-поведение когда `task_done` запускает гейты inline.

### Диагностика

| Симптом | Что проверить |
|---|---|
| Скилл зовёт legacy-форму `task_done` | v1.4 публикует единственный `tausik_task_done`. Если SKILL.md в проекте всё ещё пишет "call v2", перезапусти `python bootstrap/bootstrap.py` — `.claude/skills/` (и аналоги) обновятся под текущий контракт. |
| Verify никогда не возвращает | Запусти ту же verify-команду из обычного терминала (`.tausik/tausik verify --task <slug>`) — если работает там, но висит через extension, проблема на стороне хоста, не TAUSIK. |
| Хуки не срабатывают на `Write` | Ожидаемо — у VS Code extension нет hooks API. Агент обязан соблюдать правила без enforcement; для критичных по соблюдению задач переключайся на Claude Code CLI или Qwen Code, если важны hard-blocks. |

## Brain

| Симптом | Диагноз | Фикс |
|---|---|---|
| `brain disabled` warning | `brain.enabled=false` в config | `tausik brain init` для wizard setup |
| `Notion auth failed` | Token env var не установлена | Проверь имя env-переменной в `brain.notion_integration_token_env` |
| Brain mirror огромный | WAL не checkpoint'ится | `PRAGMA wal_checkpoint(TRUNCATE)` или удали `.tausik-brain/mirror.db-wal` |

## RAG (codebase-rag)

| Симптом | Диагноз | Фикс |
|---|---|---|
| `reindex` зависает / падает по таймауту на большом monorepo | `mode=full` обходит все tracked-файлы; на 50k+ файлах вызов превышает per-tool timeout MCP-хоста | Передай `max_seconds=N` (soft limit — вернётся частичный результат с `truncated=true`) или используй `mode=incremental` (по умолчанию; реиндексирует только файлы изменённые с `last_commit`). v1.4 пишет `[rag] indexed X/Y files, N chunks, ZZs elapsed` в stderr каждые 100 файлов — хост рендерит прогресс вместо «зависло». |

## Prompt caching не активен

Симптом: stoимость токенов на сессию растёт быстрее, чем ожидается; LLM-биллинг
показывает почти весь input как «обычный», а не как `cache_read`. Проверь через
`python scripts/validate_prompt_caching.py --auto` (или передай путь к JSONL).
Exit code 2 = API не возвращает cache-поля вовсе; exit code 1 = `cache_creation > 0`,
но `cache_read = 0` — каждый ход кешируется заново.

| Симптом | Диагноз | Фикс |
|---|---|---|
| `validate_prompt_caching.py` exit=2 (нет cache-полей) | Текущий клиент / endpoint не запрашивает caching | Используй официальный Claude Code (он включает caching по умолчанию). У сторонних оболочек проверь, что они шлют `cache_control` хотя бы на system prompt + tools. |
| Exit=1 (creation > 0, reads = 0) | Префикс нестабилен — что-то меняется между ходами | См. ниже список инвалидаторов. |
| `cache_read_input_tokens` падает к нулю в середине сессии | `tausik_update_claudemd` переписал dynamic-блок CLAUDE.md | Не запускай `update_claudemd` между tool-вызовами; держи его на границах (`/start`, `/checkpoint`, `/end`). |
| Низкий hit-rate (<50%) даже без правок CLAUDE.md | Скилл-файл (`SKILL.md`) или MCP `tools.py` редактировался в worktree между ходами | После любой правки агентских артефактов перезапусти MCP / IDE — старый префикс уже инвалидирован, продолжать сессию бессмысленно с точки зрения кеша. |
| Хочется видеть hit-rate в реальном времени | — | `python scripts/validate_prompt_caching.py --auto` после каждой длинной сессии. Записи `usage`-блоков уже лежат в `~/.claude/projects/<slug>/*.jsonl`. |

См. [architecture.md](architecture.md) секцию «Prompt caching» — там список
кешируемых поверхностей и какие правки переписывают префикс.

## Hooks

| Симптом | Диагноз | Фикс |
|---|---|---|
| Hook не срабатывает | TAUSIK_SKIP_HOOKS установлено | Проверь env, удали переменную |
| `git push` blocked | Защитный gate сработал — это нормально | Используй `/ship` или `/commit` skills (после твоего "y" они запускают `tausik push-ok && git push`). Ручная авторизация: `tausik push-ok && git push` — пишет одноразовый 60-секундный тикет, привязанный к SHA HEAD. Старый `TAUSIK_ALLOW_PUSH=1` удалён в v1.4 (был broken-by-design). Debug bypass: `TAUSIK_SKIP_PUSH_HOOK=1`. |
| Memory write blocked | Попытка записи в `~/.claude/projects/*/memory/` | Если действительно нужен cross-project memory — добавь маркер `confirm: cross-project` |
