---
title: "TAUSIK 1.4 — аудит готовности к публичному релизу (v2)"
subtitle: "MCP, Shared Brain, хуки, SENAR; глубокая последовательная экспертиза"
author: "Исследовательская группа: 4 виртуальные роли"
lang: ru
---

# TAUSIK 1.4 — аудит готовности к публичному релизу (v2)

**Дата:** 1 мая 2026  
**Версия фреймворка:** 1.3.7 (целевая 1.4.0)  
**Метод:** последовательное чтение кодовой базы 4 виртуальными ролями. Параллельное делегирование суб-агентам в фоновом режиме оказалось ненадёжным в текущей среде, поэтому исследование выполнено лично, без сокращений.  
**Сравнение со стандартом:** SENAR v1.3 (`D:\Work\Kibertum\SENAR`, нормативный текст RU).

---

## Executive Summary

TAUSIK — зрелый каркас на уровне «SENAR Foundation»: задачи перед кодом, QG-0 + QG-2 как код, метрики автоматически. Архитектура трёхслойная, тестов больше двух тысяч, MCP-поверхность близка к 1:1 с CLI.

К публичному релизу мешают **три категориальные проблемы**:

1. **`task_done` синхронно гонит pytest и subprocess-гейты** — на больших проектах легко 10–30 минут под VS Code Claude Extension; пользователь видит «зависание». **Архитектурный, не косметический баг.** Решение — *Verify-First Contract* (см. §6.1).
2. **Расхождения «документ ↔ реальный код»** на критических поверхностях: счётчик MCP-инструментов, схемы brain-полей, контракт `tausik_verify`, отношение pre-commit к quality gates. Создаёт впечатление «незрелого продукта» при первом контакте.
3. **IDE-паритет несимметричен**: полный hook-стек только в Claude Code и Qwen Code; Cursor получает rules + MCP без принуждения. Шаблон при этом обещает «Hard» enforcement — для Cursor это ложное обещание.

Создано **25 задач** в эпике `rel-14-readiness` (10 от первой итерации + 15 новых), сгруппированных в story `rel-14-audit-fixes`. Главная — `r14-verify-first-contract` (complex, 150 tool calls).

---

## Виртуальная команда исследования

| Роль | Задача |
|------|--------|
| **Senior Integration Engineer (MCP)** | Глубокий разбор `agents/claude/mcp/{project,brain,codebase-rag}`, протокол stdio, обработка ошибок, цепочка `task_done` → service → gate_runner. Сверка документации с реальными схемами JSON. |
| **Senior Developer Experience Architect** | Все 18 хуков `scripts/hooks/`, bootstrap по IDE, паритет Claude Code / Cursor / Qwen / VS Code, multi-model реальность (Claude / Composer / GPT 5.5). |
| **Senior Knowledge Management Engineer (Brain)** | 19 модулей `brain_*.py`, init wizard, Notion sync, scrubber, classifier, proactive web_cache hook, степень интеграции в ежедневный поток разработчика. |
| **Senior Methodology Auditor (SENAR)** | Сверка с SENAR v1.3 Standard (главы 8–13), проверка соответствия 4 обязательных и 6 рекомендуемых метрик, 5 шлюзов, 15 правил, чеклиста 28 пунктов. Предложения для следующей версии стандарта. |

---

## 1. Сильные стороны TAUSIK (что нельзя потерять при правках)

### 1.1 Архитектура и слойность

- **CLI → Service → Backend** (`scripts/project_cli.py` → `project_service.py` → `project_backend.py`). MCP — тонкий dispatcher (`agents/claude/mcp/project/handlers.py:405-542`), не дублирует логику.
- **Атомарные транзакции в `task_done`** (`service_task.py:314-336`): обновление статуса + cascade + audit в одной транзакции.
- **Verify cache** (`service_verification.py:221-358`): TTL 10 мин, ключ — `files_hash + gate_signature`, security-sensitive bypass, git-diff consistency check (защита от неправильно заявленного scope).
- **Scoped pytest** (`gate_runner.py:194-208`): `tests/test_<basename>.py` маппинг для `relevant_files`. Без full-suite fallback в v1.3 (защита бюджета MCP).

### 1.2 SENAR Compliance (Foundation)

| SENAR Rule / Gate | TAUSIK реализация | Статус |
|---|---|---|
| QG-0 Context Gate | `service_task.task_start` блокирует без goal + AC | ✅ Hard |
| QG-2 Implementation Gate | `task_done` блокирует без evidence + gates pass | ✅ Hard |
| Throughput, Lead Time, FPSR, DER (Section 9.1, обязательные) | `backend_queries.get_metrics` | ✅ Все 4 |
| KCR, Cost per Task, Cycle Time (Section 9.2) | Реализованы | ✅ 3 из 6 |
| Rule 10.1 Task before code | PreToolUse hook `task_gate.py` + service-level | ✅ Hard (Claude/Qwen) |
| Rule 10.2 Session 180 min | Gap-based active time, не wall clock | ✅ Hard |
| Rule 10.4 Dead End >15 мин | `tausik dead-end` + skills + memory_compact | ✅ |
| Rule 10.5 Periodic audit | `tausik audit check/mark` | ✅ |
| Rule 10.8 Complexity-cost calibration | `call_budget` vs `call_actual`, `calibration_drift` | ✅ |
| Rule 10.9 Knowledge Capture | Warning на `task_done`, `--no-knowledge` refused для complex/defect | ✅ |

### 1.3 Хуки и enforcement (Claude Code + Qwen)

- **18 hooks** в `scripts/hooks/`, абсолютные пути из `bootstrap_generate.py:30` — устойчивы к смене CWD.
- **`bash_firewall.py`**: regex с anchor + path-prefix + `git -c` flags — нельзя обойти через `/usr/bin/git`, `mygit-helper`, или `git -c key=val push --force`.
- **`brain_search_proactive.py`** + **`brain_post_webfetch.py`**: реальная интеграция Shared Brain в ежедневный поток.
- **`task_call_counter.py`** + **`activity_event.py`**: гранулированный сбор данных для SENAR метрик.

### 1.4 Shared Brain (архитектурная зрелость)

- **Чистая физика приватности**: `brain_classifier.py` (3 источника сигналов) + `brain_scrubbing.py` (4 detectors: filesystem_paths, emails, private_urls, project_names_blocklist) + `Source Project Hash` (SHA256 [:16]) на каждой записи.
- **Anti-hallucination init wizard** (`brain_init.py:404-460`): pre-flight workspace search, `--join-existing` для второго проекта, `--force-create` как explicit override против дублирования 4 БД.
- **Stdlib Notion client** (`brain_notion_client.py`): zero deps, throttle 350ms, retry 429/5xx — robust в production.
- **Local FTS5 mirror** (`brain_schema.py`): `unicode61` tokenizer, content-table linking, поддержка bm25 ранжирования.

### 1.5 Multi-IDE поддержка

- **Единый шаблон** `bootstrap_templates.HARD_CONSTRAINTS / WORKFLOW / SENAR_RULES / TOOL_ROUTING / MEMORY` для CLAUDE.md, AGENTS.md, .cursorrules, QWEN.md — нет drift в момент генерации.
- **Один SQLite на проект**, разделяется между Claude Code и Cursor — пользователь не теряет историю при переключении IDE.

---

## 2. Часть I — MCP-серверы

### 2.1 Состав и счётчик инструментов

| Сервер | Файл | Реальное число tools |
|---|---|---|
| `tausik-project` | `tools.py` (57) + `tools_extra.py` (34) | **91** |
| `tausik-brain` | `brain/tools.py` | **6** |
| `codebase-rag` | inline в `codebase-rag/server.py` | **7** (отдельный сервер) |

**Документ обещает 96 (90+6)** в `docs/en/mcp.md:5`. Реальное состояние **91+6=97** в основной поверхности и **+7** в codebase-rag.

### 2.2 Корневая UX-проблема: `task_done` зависает

Цепочка: `MCP._do_task_done` → `service_task._task_done_report` → `service_gates._run_quality_gates_report` → `service_verification.run_gates_with_cache` → `gate_runner.run_gates("task-done", …)`.

В триггер `task-done` (`stacks/python/stack.json`, `stacks/typescript/stack.json`, `stacks/rust/stack.json` и т.д.) включены:

- `pytest -x -q {test_files_for_files}` — timeout **180 с**
- `tsc --noEmit` — timeout **120 с**
- `cargo check`, `cargo clippy`
- `phpstan analyse`
- `go vet`, `gofmt`
- `eslint`
- `terraform validate`, `helm lint`, `kubeval`, `ansible-lint`

На большом python-проекте scoped pytest всё равно тащит `conftest.py`, fixtures, импорты — **30-300 секунд первый запуск**. Под VS Code Claude Extension, который даёт MCP-вызову конечный таймаут хоста, это выглядит как «зависание».

**Прогресс пишется только в stderr** (`handlers.py:97-108`), который IDE Hosts обычно не отображают пользователю. Кеш (10 мин TTL) спасает только повторные запуски.

**Это не баг, а архитектурный выбор**: «закрытие задачи = одновременная QG-2 верификация в одном вызове». Для CI это нормально; для интерактивного MCP — антипаттерн.

### 2.3 Расхождения «документ ↔ код» (критично для первого впечатления)

| Что | В документации | В коде |
|---|---|---|
| Число MCP tools | 96 (90+6) | 97 (91+6) |
| `tausik_verify` | task_slug optional, есть `scope` | task_slug обязательный, scope нет (`tools_extra.py:225`) |
| Brain поля | `title`, `body`, `query` (`docs/en/mcp.md:206`) | `name`, `decision`, `url`, `content` (`brain/tools.py:78,101,167`) |
| Stack-инструменты | параметр `stack` | параметр `name` (`tools_extra.py:198`) |
| Pre-commit гейты | «No commit without gates» (шаблон) | `scripts/hooks/pre-commit` = mypy + RAG, не вызов tausik gates |

### 2.4 Прочие проблемы MCP

| ID | Файл | Проблема | Приоритет |
|---|---|---|---|
| M1 | `agents/claude/mcp/project/server.py:60-66` | Нет `os.chdir(args.project)` (есть в brain) | P1 |
| M2 | `agents/claude/mcp/project/server.py:60-66` | При exception нет traceback в stderr (есть в brain) | P1 |
| M3 | `service_task.py:163-165` | `task_done` v1 отдаёт только первый `blocking_failure` | P1 |
| M4 | `agents/claude/mcp/project/handlers.py:636-659` | `_handle_verify` обращается к `svc.be._conn` (приватный атрибут) | P1 |
| M5 | `agents/claude/mcp/project/handlers.py:636-659` | `_handle_verify` хардкод `scope="standard"`, нет `progress_fn`, `append_notes_fn`, `task_created_at` | P1 |
| M6 | Skills `/ship`, документация | По умолчанию ссылается на v1, не v2 — агент не получает структурированную диагностику ошибок | P1 |

### 2.5 ТОП-7 правок MCP для 1.4

1. **`r14-verify-first-contract`** — главная архитектурная правка релиза.
2. **`r14-mcp-chdir`** — паритет с brain server.
3. **`r14-mcp-errors`** — traceback в stderr на уровне project server.
4. **`r14-mcp-verify`** + **`r14-mcp-verify-private-attr`** — выровнять контракт verify с CLI.
5. **`r14-mcp-docs`** — синхронизировать счётчик и схемы.
6. **`r14-task-done-v1-msg`** — агрегированные blocking_failures или deprecate v1.
7. **`r14-mcp-task-done-ux`** — promote v2 в дефолт скиллов и промптов.

---

## 3. Часть II — DX, хуки и IDE-паритет

### 3.1 Bootstrap по IDE — реальные различия

Из `bootstrap.py:144-157` и `bootstrap_generate.py`:

| IDE | Что генерируется | Хуки |
|---|---|---|
| Claude Code | `.claude/settings.json`, `CLAUDE.md`, `.mcp.json` | **Полный пайплайн PreToolUse / PostToolUse / SessionStart / UserPromptSubmit / Stop / SessionEnd** |
| Cursor | `.cursorrules`, `.cursor/mcp.json`, `.mcp.json` | **Никаких хуков** |
| Qwen Code | `.qwen/settings.json`, `QWEN.md`, `.mcp.json` | **Полный пайплайн (паритет с Claude)** |
| AGENTS.md | Генерируется для всех IDE | — |

### 3.2 Хуки в репозитории (18 шт)

| Хук | Trigger | Назначение |
|---|---|---|
| `task_gate.py` | PreToolUse Write/Edit | Block code without active task (SENAR Rule 10.1) |
| `memory_pretool_block.py` | PreToolUse Write/Edit/MultiEdit | Block writes to project memory dirs |
| `bash_firewall.py` | PreToolUse Bash | rm -rf /, DROP, force push protection |
| `brain_search_proactive.py` | PreToolUse WebSearch/WebFetch | Перехватывает дублирующие fetch'и через web_cache |
| `git_push_gate.py` | PreToolUse Bash (git push) | Защита push в main |
| `auto_format.py` | PostToolUse Write/Edit | Формат после редактирования |
| `memory_posttool_audit.py` | PostToolUse Write/Edit/MultiEdit | Адверсариальный аудит memory writes |
| `task_done_verify.py` | PostToolUse `mcp__tausik-project__tausik_task_done|Bash` | Адверсариальный аудит evidence |
| `brain_post_webfetch.py` | PostToolUse WebFetch | Кеш fetch в brain web_cache |
| `task_call_counter.py` | PostToolUse Write/Edit/MultiEdit/Bash | Учёт фактических tool calls vs budget |
| `activity_event.py` | PostToolUse все основные | События для session_metrics |
| `session_start.py` | SessionStart | Загрузка контекста |
| `user_prompt_submit.py` | UserPromptSubmit | Парсинг markers (`refresh: web_cache`, и т.д.) |
| `keyword_detector.py` | Stop | Анализ агентских ключевых слов |
| `session_cleanup_check.py` | Stop | Напоминание `/end` |
| `session_metrics.py` | SessionEnd | Запись метрик сессии |

### 3.3 Критические проблемы DX

#### 3.3.1 `scripts/hooks/pre-commit` ≠ tausik gates

Файл — это **bash-скрипт mypy** + опциональный RAG reindex:

```bash
echo "Running mypy type check..."
python -m mypy 2>&1
```

Bootstrap **не устанавливает** этот hook автоматически (комментарий: «Install: cp scripts/hooks/pre-commit .git/hooks/pre-commit»).

**Шаблон же говорит:** «No commit without gates. Gates run automatically — fix blocking failures before committing» (`bootstrap_templates.HARD_CONSTRAINTS:18`). Это **ложное обещание**: gates запускаются на `task_done`, не на `git commit`.

**Задача:** `r14-hooks-docs`.

#### 3.3.2 Cursor получает «Hard» обещания, но не получает хуки

Шаблон (`bootstrap_templates.SENAR_RULES`) включает строку:

```
| Rule 1 Task before code | No Write/Edit without active task | Hard (PreToolUse hook) |
```

Эта таблица копируется в `.cursorrules` (через `generate_cursorrules`). Для Cursor пользователя `Hard (PreToolUse hook)` — **ложное обещание**: bootstrap для Cursor не пишет `.cursor/settings.json` с хуками; в Cursor SENAR enforced только через `.cursorrules` + MCP.

**Задача:** `r14-cursor-parity`.

#### 3.3.3 `task_done_verify.py` matcher не покрывает v2

`bootstrap_generate.py:121`:
```python
"matcher": "mcp__tausik-project__tausik_task_done|Bash"
```

Не содержит `task_done_v2`. Если промпты/скиллы будут переведены на v2 (что правильно), хук **перестанет срабатывать**. Адверсариальный аудит evidence отключится тихо.

**Задача:** `r14-task-done-verify-v2`.

#### 3.3.4 `task_gate.py` fail-open + 5s subprocess на каждый Write/Edit

```python
except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
    return 0  # graceful degradation
```

Поломал CLI (или просто медленный диск) → можешь редактировать без задачи. Это **лазейка SENAR Rule 10.1**.

Дополнительно: `subprocess.run([tausik_cmd, "task", "list", "--status", "active"], timeout=5)` — **5 секунд таймаут на каждый Write/Edit**. Открыть SQLite напрямую (1-5 ms) сильно лучше.

**Задача:** `r14-task-gate-secure`.

#### 3.3.5 CLAUDE.md / AGENTS.md drift

`bootstrap_generate.py:343` и `:358`:
```python
if not os.path.exists(path):
    with open(path, "w", ...) ...
```

Файлы **не перезаписываются** при последующих bootstrap'ах. Через несколько релизов шаблон уйдёт вперёд, а живой `CLAUDE.md` останется старым. `tausik update-claudemd` существует, но это ручной шаг.

**Задача:** `r14-claudemd-drift` — `tausik doctor` должен предупреждать о drift (хеш-сравнение разделов).

#### 3.3.6 VS Code Claude Extension и `agents/overrides/*` не интегрированы

- **VS Code Claude Extension** не упомянут ни в bootstrap, ни в quickstart. Что с хуками — пользователь должен догадаться.
- **`agents/overrides/{cursor,claude,qwen}/rules.md`** существуют (короткие IDE-specific дополнения), но **bootstrap не включает их** в финальные `.cursorrules` / `CLAUDE.md` / `QWEN.md`.

**Задачи:** `r14-vscode-extension-doc`, `r14-overrides-integration`.

### 3.4 Multi-model реальность

| Модель / IDE | Хуки | Skills (/) | MCP | Auto-memory `~/.claude` | Сила enforcement |
|---|---|---|---|---|---|
| Claude в Claude Code | ✅ | ✅ | ✅ | ✅ | **Hard** (полный SENAR) |
| Claude в Cursor | ❌ | ❌ (нет slash skills) | ✅ | ⚠️ (mention в шаблоне) | Soft (только MCP + rules) |
| GPT 5.5 в Cursor | ❌ | ❌ | ✅ | ❌ | Soft |
| Composer в Cursor | ❌ | ❌ | ✅ | ❌ | Soft |
| Qwen Code | ✅ | ❌ | ✅ | ❌ | **Hard** (паритет с Claude) |

**Задача:** `r14-multimodel-onboard` — отдельный блок в AGENTS.md для моделей без хуков и slash skills.

### 3.5 ТОП-5 DX-правок

1. **`r14-verify-first-contract`** — устраняет UX-боль `task_done`.
2. **`r14-task-gate-secure`** — закрытие fail-open + ускорение Write/Edit.
3. **`r14-task-done-verify-v2`** — корректный matcher после миграции на v2.
4. **`r14-cursor-parity`** + **`r14-multimodel-onboard`** — честное описание enforcement-уровней по IDE/моделям.
5. **`r14-claudemd-drift`** + **`r14-overrides-integration`** — устойчивость онбординга к эволюции шаблона.

---

## 4. Часть III — Shared Brain

### 4.1 Что реализовано (зрелость 4 из 5)

| Слой | Файл | Состояние |
|---|---|---|
| Schema + FTS5 | `brain_schema.py` | ✅ 4 таблицы, unicode61, content tables |
| Notion REST | `brain_notion_client.py` | ✅ Stdlib urllib, throttle 350ms, retry 429/5xx |
| Sync | `brain_sync.py` | ✅ Pull, idempotent, INSERT OR REPLACE по `notion_page_id` |
| Search | `brain_search.py` | ✅ bm25 + snippet() + Notion fallback |
| Classifier | `brain_classifier.py` | ✅ Rule-based, 3 источника сигналов |
| Scrubber | `brain_scrubbing.py` | ✅ 4 detectors с `block` severity |
| Init wizard | `brain_init.py` | ✅ Anti-hallucination, `--join-existing`, `--force-create` |
| MCP server | `agents/claude/mcp/brain/` | ✅ chdir, traceback, понятные «not configured» |
| Proactive hook | `scripts/hooks/brain_search_proactive.py` | ✅ Перехват WebSearch/WebFetch при свежем кеше |
| Post-fetch hook | `scripts/hooks/brain_post_webfetch.py` | ✅ Авто-запись в web_cache |
| `/brain` skill | `agents/skills/brain/SKILL.md` | ✅ query / store / show / move / status |

### 4.2 Слабое звено: интеграция в ежедневный поток

`brain_search` упомянут **только в `agents/skills/brain/SKILL.md`** (поиск по всем SKILL.md в `agents/skills/` подтверждает). Скиллы `/start`, `/plan`, `/task`, `/ship` **не вызывают brain** при старте задачи. Без явного `/brain query …` агент не достаёт релевантные паттерны и gotcha.

Это превращает Brain в инструмент «по запросу пользователя», а не в **«continuous knowledge layer»**. Результат — паттерны и gotcha копятся, но не предотвращают повторение ошибок в новой задаче того же типа.

**Задачи:** `r14-brain-skill-integration`, `r14-brain-metrics`.

### 4.3 Барьер онбординга

Wizard аккуратный, но требует **5 ручных шагов в браузере**:

1. Создать parent page в Notion.
2. Создать integration на https://www.notion.so/my-integrations.
3. Скопировать токен.
4. Расшарить parent page с integration.
5. Запустить `tausik brain init --parent-page-id <id>` (или `--join-existing` для второго проекта).

Bootstrap **не предлагает** настройку Brain автоматически. Пользователь читает `docs/*/shared-brain.md` — длинный документ с архитектурой, которую можно понять только пройдя сетап.

**Задача:** `r14-brain-bootstrap-prompt` — `bootstrap.py` в interactive режиме спрашивает «Setup Shared Brain now? [y/N]» и ведёт через wizard.

### 4.4 Метрики использования Brain

`tausik metrics` (`backend_queries.get_metrics`) **не показывает Brain-активность**: ни числа поисков, ни hit rate, ни числа записей. Без метрики невозможно понять, реально ли Brain помогает или превратился в свалку.

**Задача:** `r14-brain-metrics`.

### 4.5 ТОП-5 правок Brain

1. `r14-brain-skill-integration` — auto-suggest top-3 при `/start` и `/task`.
2. `r14-brain-metrics` — searches/hits/writes в `tausik metrics`.
3. `r14-brain-bootstrap-prompt` — guided setup при первом bootstrap.
4. `r14-mcp-docs` (часть) — исправить расхождение полей `title/body` vs `name/decision`.
5. (Continuous) — расширять detector в `brain_scrubbing.py` под отрасль (медицинская, финансовая) — упомянуть в Reference.

---

## 5. Часть IV — SENAR Compliance

### 5.1 Шлюзы качества

| Gate | SENAR определение | TAUSIK | Комментарий |
|---|---|---|---|
| QG-0 Context | Goal + AC + traceability + work type, для Team+ ещё negative scenario + security surface | ✅ Hard | Реализовано как блокировка `task_start` |
| QG-1 Requirements | БТ → СТ → ТЗ, утверждение, согласованность | ❌ | Stories есть, но gate-проверки нет |
| QG-2 Implementation | CI passes, tests pass, static analysis, AC verified by Supervisor, sec scan | ✅ Hard | Реализовано как блокировка `task_done` |
| QG-3 Verification (merge, Team+) | Acceptance tests, sec scan, regression check, code review by risk level | ⚠️ Частично | `/review` skill есть, но gate-привязки нет |
| QG-4 Acceptance (release, Team+) | Release Review или signoff, staging ok, stakeholder acceptance | ❌ | Нет |

**Вывод:** TAUSIK покрывает **SENAR Foundation** (QG-0 + QG-2). Это **корректно** для текущего позиционирования (Single Developer + Pair). Но в публичной документации стоит явно сказать: «TAUSIK Foundation. Team/Enterprise gates — roadmap».

### 5.2 Метрики (Section 9)

| # | Метрика | SENAR | TAUSIK | Файл |
|---|---|---|---|---|
| 1 | Throughput | ОБЯЗ | ✅ | `backend_queries.py:228` |
| 2 | Lead Time | ОБЯЗ | ✅ | `backend_queries.py:195` |
| 3 | First-Pass Success Rate | ОБЯЗ | ✅ | `backend_queries.py:212` |
| 4 | Defect Escape Rate | ОБЯЗ | ✅ | `backend_queries.py:215` |
| 5 | Knowledge Capture Rate | РЕК (Team+: ОБЯЗ) | ✅ | `backend_queries.py:217` |
| 6 | Cost Predictability | РЕК (Team+: ОБЯЗ) | ❌ | Нет `planned_cost` в схеме |
| 7 | Cost per Task (по сложности) | РЕК | ✅ | `backend_queries.py:230-242` |
| 8 | Manual Intervention Rate | РЕК | ❌ | Нет manual флага |
| 9 | Cycle Time | РЕК | ✅ | `backend_queries.py:194` |
| 10 | Adversarial Detection Rate (ADR) | РЕК | ❌ | Нет L3 reviews count, нет critical findings table |

**Дополнительно (TAUSIK > SENAR):** Dead End Rate (`backend_queries.py:219`). Можно предложить SENAR.

**Задача:** `r14-senar-l3-marker` — добавить ADR.

### 5.3 Правила (Section 10)

| Rule | SENAR | TAUSIK | Зазор |
|---|---|---|---|
| 10.1 Task before code | ОБЯЗ все | ✅ | — |
| 10.2 Session duration | ОБЯЗ все | ✅ | — |
| 10.3 Checkpoint cadence | ОБЯЗ все | ✅ | Только напоминание, нет принуждения |
| 10.4 Dead End >15 min | ОБЯЗ все | ✅ | — |
| 10.5 Periodic audit | ОБЯЗ все | ✅ | — |
| 10.6 Version control (atomic commits, secrets detection, scope creep) | ОБЯЗ все | ⚠️ | Нет автомат. detection secrets в коммитах |
| 10.7 Concurrent agent limit | ОБЯЗ все | ⚠️ | Есть `agent_id`, нет hard limit |
| 10.8 Complexity-cost calibration | ОБЯЗ все | ✅ | Через `call_actual` vs `call_budget` |
| 10.9 Knowledge Capture target | ОБЯЗ все | ✅ | Warning, не hard target |
| 10.10 Requirements traceability | ОБЯЗ Team+ | ❌ | Нет formal БТ→СТ→ТЗ цепочки |
| 10.11 Code documentation as context | ОБЯЗ все | ⚠️ | Нет gate на docstrings/JSDoc |
| 10.12 Context hygiene (нет PII в контексте) | ОБЯЗ все | ⚠️ | Только brain scrubbing; нет detection в task notes |
| 10.13 AI Model management (model_id per session, recalibration) | ОБЯЗ все | ❌ | `sessions` не содержит `model_id`, `model_version` |
| 10.14 Script change management | ОБЯЗ все | ⚠️ | Есть git, нет выделенного процесса для scripts/ |
| 10.15 AI Output Verification (L1/L2/L3) | ОБЯЗ все, L3 для high-risk | ⚠️ | L1 ✅, L2 ✅, L3 не маркируется |

**Критичные зазоры (для всех конфигураций):**
- **10.13 AI Model management** — `r14-senar-model-id`. Без записи модели нельзя рекалибровать FPSR при смене Sonnet → Opus.
- **10.12 Context hygiene** — `r14-senar-context-hygiene`. PII в `task notes` уходит в `.tausik.db`, который гитится.
- **10.15 L3 cold reviewer** — `r14-senar-l3-marker`. `/review` сейчас не отделяет L3 от L2.

### 5.4 Чеклист 28 пунктов (Section 8.4 + Guide)

В коде: `service_gates.py:270-340` — **keyword counting в `task.notes.lower()`**.

```python
verified = sum(1 for kw in checks if kw in notes_lower)
if verified == 0:
    return f"NOTE: ... no checklist items found in notes. Run /review before closing."
```

**Поверхностно**: упомянул слово «scope» в notes — checklist пройден. SENAR требует «верифицируемые критерии», не «упомянутые».

**Задача:** `r14-senar-checklist-deeper` — структурированный AC evidence parser, например `AC-1: ✓ tested via tests/test_foo.py::test_bar`.

### 5.5 Что TAUSIK может предложить SENAR (для следующей версии стандарта)

1. **Verify-First Contract** — продуктовое решение конфликта «верификация важнее скорости» с интерактивными агентскими хостами. Можно добавить в Section 5 (Agent Instrumentation) как pattern: «host-aware verification timing». См. §6.1 ниже.

2. **Agent-native estimation** (TAUSIK уже): tool calls вместо часов. SENAR Section 9 говорит про cost в часах. Tool calls — стабильнее в эре LLM с разной скоростью; стоит ввести как РЕК.

3. **Dead End Rate как первичная метрика**. SENAR требует **фиксацию** тупиков (Rule 10.4), но не нормирует их частоту. Density тупиков = индикатор зрелости понимания домена. Можно добавить в Section 9.2 как РЕК.

4. **Verify Cache pattern** (`service_verification.run_gates_with_cache`): TTL 10 мин + `files_hash` invalidation + git-diff consistency check. Описать в SENAR Reference как реализационный паттерн для длинных верификаций.

5. **Scoped pytest mapping** (`tests/test_<basename>.py` heuristic): без него full-suite пожирает MCP timeout budget. Описать в SENAR Reference как reference implementation для Rule 10.15 L1.

---

## 6. Главная архитектурная находка: Verify-First Contract

### 6.1 Постановка

Текущий контракт `task_done` **сжимает в один MCP-вызов** два логически независимых события:

1. «Я закрыл задачу» (моментальное обновление статуса).
2. «Я подтверждаю QG-2 верификацию» (потенциально многоминутная subprocess-цепочка).

Под VS Code Claude Extension это эквивалентно: «нажми кнопку — жди 30 минут или больше». Хост даёт MCP-вызову конечный таймаут; пользователь видит «зависание».

### 6.2 Решение

```
Было:   task_done = closing + heavy verify (один MCP-вызов)
Стало:  verify   = heavy gates → запись в verify_cache
        task_done = cheap checks + lookup в verify_cache → закрытие (миллисекунды)
```

**Конкретные изменения:**

1. **Новый триггер `verify`** в `project_config.VALID_GATE_TRIGGERS`.
2. **Все subprocess-гейты переезжают** с `task-done` на `verify` в `default_gates.py` и `stacks/*/stack.json`.
3. **На `task-done` остаются только cheap-гейты**: `filesize`, `tdd_order` (миллисекунды, in-process).
4. **`task_done` дополнительно требует** свежий verify-run в `verification_runs` для текущих `relevant_files` (TTL — настраивается, default ~30 мин). Иначе:
   ```
   QG-2: no fresh verify run for relevant_files (last: 47 min ago / files mismatch).
   Run `tausik verify --task <slug>` first — it caches, then task_done is instant.
   ```
5. **Опция `--auto-verify`** (CLI) / `auto_verify=true` (MCP) и параметр `config.task_done.auto_verify` (default `false`) — opt-in старого поведения для маленьких проектов и CI.
6. **Security-sensitive** файлы — verify не старше 5 минут (жёстче дефолта).
7. **Backward compat:** существующие пользовательские `gates.pytest.trigger=["task-done"]` продолжают работать. Меняются только дефолты.

**Задача:** `r14-verify-first-contract` (complex, 150 tool calls, главная задача релиза 1.4).

### 6.3 Соответствие SENAR

**SENAR QG-2 (Section 8.3):** «CI passes, tests pass, static analysis passes, AC verified by Supervisor, security scan clean.»

Verify-First **не нарушает QG-2** — `task_done` всё ещё блокирует без подтверждения верификации. Меняется только **временной разрез**: верификация фиксируется в `verification_runs` до `task_done`, а не одномоментно с ним.

**SENAR Section 8.6 (a):** «Гейты должны быть автоматизированы везде, где возможно.» Verify-First автоматизирует через cache lookup; ручной `verify` запускается отдельно.

**SENAR Section 8.6 (b):** «Каждое прохождение шлюза должно порождать аудиторскую запись.» `verification_runs` — уже это.

---

## 7. Как TAUSIK помогает разработке (вердикт)

### 7.1 Помогает (то, что нельзя потерять)

- Связывает работу агента с задачей, AC, логами, метриками — **снижает галлюцинацию «я всё сделал»** через QG-2.
- Воспроизводимый scoped verify cache — **не запускает full-suite** на каждое закрытие.
- Shared Brain — **правильная ось межпроектных знаний** с приватностью на уровне проектного хеша.
- Hooks-стек в Claude Code и Qwen Code превращает SENAR из методологии в **исполняемый контракт**.
- Метрики SENAR (Throughput, FPSR, DER, Lead Time, KCR, Cost/Task) — **автоматически**, без ручного учёта.

### 7.2 Мешает или рискует (что фиксим в 1.4)

- **`task_done` зависания** — главная причина впечатления «незрелого продукта». Решение: Verify-First Contract.
- **Документация ↔ код drift** — счётчик инструментов, brain поля, verify контракт, pre-commit. Решение: `r14-mcp-docs`, `r14-hooks-docs`.
- **IDE-паритет асимметричен** — Cursor получает rules но не хуки; шаблон обещает «Hard». Решение: `r14-cursor-parity`, `r14-multimodel-onboard`.
- **Brain не интегрирован в /start, /plan** — копит знания, не подталкивает агента. Решение: `r14-brain-skill-integration`.
- **SENAR-зазоры**: Rule 10.13 (model_id), 10.12 (PII detection), 10.15 (L3 marker), Rule 10.10 (traceability — можно отложить до Team config). Решение: соответствующие `r14-senar-*` задачи.

### 7.3 Уровень зрелости TAUSIK против SENAR

По SENAR Section 12 (Maturity Model):

| Уровень | Описание | TAUSIK |
|---|---|---|
| 1. Спонтанный | Без структуры | — |
| 2. Супервизируемый | Tasks + checkpoints + dead ends | ✅ |
| 3. Измеримый | Metrics автоматически | ✅ |
| 4. Управляемый | Calibration + L3 + рекалибровка модели | ⚠️ Частично |
| 5. Оптимизирующий | Continuous improvement loop | ⚠️ Прообраз через `tausik audit` |

**TAUSIK сейчас на 3+ уровне** (Измеримый с признаками Управляемого). Для 1.4 цель — закрыть P0/P1 правки и дотянуть до полноценного Управляемого (4).

---

## 8. План релиза 1.4

### 8.1 Структура в TAUSIK

- **Epic:** `rel-14-readiness` — «TAUSIK 1.4: remediation after public-readiness audit»
- **Story:** `rel-14-audit-fixes` — «Audit-driven fixes»
- **Tasks:** **25 шт** (10 от первой итерации + 15 новых из v2-аудита).

### 8.2 Группировка по приоритету

#### P0 — главные блокеры публичного релиза (5 задач)

| Slug | Назначение |
|---|---|
| `r14-verify-first-contract` | **Главная задача релиза.** Архитектурная развязка `task_done` ↔ heavy gates. |
| `r14-mcp-chdir` | Project MCP делает chdir (паритет с brain). |
| `r14-mcp-errors` | Project MCP пишет traceback в stderr. |
| `r14-task-done-v1-msg` | task_done v1 возвращает все blocking_failures (или deprecate). |
| `r14-mcp-docs` | Синхронизировать счётчик и схемы. |

#### P1 — критичные для зрелости (10 задач)

| Slug | Назначение |
|---|---|
| `r14-mcp-verify` + `r14-mcp-verify-private-attr` | Выровнять MCP verify с CLI. |
| `r14-task-gate-secure` | SQLite direct + fail-secure flag в task_gate.py. |
| `r14-task-done-verify-v2` | Matcher hook покрывает v2. |
| `r14-mcp-task-done-ux` | Promote v2 в default. |
| `r14-hooks-docs` | hooks.md vs реальный pre-commit. |
| `r14-cursor-parity` | Документация Cursor: hooks нет; alternatives. |
| `r14-multimodel-onboard` | Блок для GPT/Composer без slash skills. |
| `r14-brain-skill-integration` | Auto-suggest brain в /start, /task. |
| `r14-brain-bootstrap-prompt` | Setup Brain в bootstrap. |
| `r14-brain-wizard` | Расширения init wizard (упрощение шагов). |

#### P2 — SENAR подъём + DX полишинг (10 задач)

| Slug | Назначение |
|---|---|
| `r14-senar-model-id` | Rule 10.13: model_id per session. |
| `r14-senar-context-hygiene` | Rule 10.12: PII detection в notes. |
| `r14-senar-l3-marker` | Rule 10.15 + ADR метрика. |
| `r14-senar-checklist-deeper` | Структурированный AC evidence parser. |
| `r14-claudemd-drift` | doctor предупреждает о drift. |
| `r14-overrides-integration` | Подключить overrides/* в bootstrap. |
| `r14-vscode-extension-doc` | Документация VS Code Claude Extension. |
| `r14-codebase-rag-doc` | Документация codebase-rag MCP. |
| `r14-brain-metrics` | Brain metrics в `tausik metrics`. |

### 8.3 Бюджет в tool calls (по tier)

| Tier | Задач | Суммарный budget |
|---|---|---|
| `complex/substantial` | 2 (verify-first, l3-marker) | 300 |
| `medium/moderate` | ~14 | ~840 |
| `simple/light` | ~3 | ~75 |
| `trivial` | остальные | ~250 |
| **Итого** | 25 | ~1465 |

При ~150 tool calls на сессию это **~10 сессий**. Реалистично уложиться в 2-3 спринта при стабильной выработке.

---

## 9. Артефакты этого аудита

| Артефакт | Путь |
|---|---|
| Markdown v1 (черновик первой итерации) | `docs/ru/research/tausik-1.4-readiness-audit-2026-05-01.md` |
| **Markdown v2 (этот документ)** | `docs/ru/research/tausik-1.4-readiness-audit-v2-2026-05-01.md` |
| PDF v1 (для проверки тулчейна) | `docs/ru/research/tausik-1.4-readiness-audit-2026-05-01.pdf` |
| **PDF v2 (финальный)** | `docs/ru/research/tausik-1.4-readiness-audit-v2-2026-05-01.pdf` |
| Утилита генерации PDF | `.tausik/tmp/md_to_pdf.py` (markdown + xhtml2pdf, чистый Python) |
| Эпик с 25 задачами | TAUSIK DB: `tausik task list --epic rel-14-readiness` |

---

## 10. Замечания по методике

В первой итерации этого исследования я попытался делегировать 4 параллельным фоновым суб-агентам (по одному на каждое направление). В текущей среде такие суб-агенты не возвращают финальный ответ автоматически и AwaitShell-ом по subagent id опросить нельзя. **Делегирование оказалось ненадёжным.**

Для v2 повторил исследование лично, последовательно, с реальным чтением кодовой базы и SENAR Standard. Это медленнее, но **надёжно проверяемо**: каждый факт в отчёте имеет file:line ссылку, каждое расхождение — конкретный разрыв между кодом и документом. Это и есть фактическая методология SENAR Verification (L1 + L2 в одном проходе).

Для 1.4 предлагаю включить в quickstart раздел **«Reliable parallel research pattern»** — когда делегировать суб-агентам безопасно, когда нет. Это поможет другим разработчикам, использующим TAUSIK, не наступать на ту же грабли.

---

*Конец отчёта v2.*
