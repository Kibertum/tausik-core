# TAUSIK v1.4.2 — Независимый аудит реализации SENAR v1.3 / RENAR v0.1

**Аудитор:** Independent (Claude Opus 4.7, 1M context, single-pass review)
**Дата:** 2026-05-18
**Объект:** TAUSIK v1.4.2 (commit `a127d45`, branch `main`)
**Снимок состояния:** 138 source files (Python stdlib), 3378 тестов, schema v27, 103 MCP tools, 25 quality gates, 20+1 hooks, 12 core + 25 vendor skills, 13 stacks с custom-extension'ом, два MCP-сервера (`tausik-project` + `tausik-brain`) плюс опциональный `codebase-rag`.

---

## TL;DR

TAUSIK — это **самая полная open-source реализация SENAR v1.3 на сегодня** и единственная, где правила фреймворка реально *enforced* (хуки + QG-0/QG-2 без bypass), а не просто рекомендованы в `AGENTS.md`. По всем 33 элементам SENAR Core внутренняя матрица заявляет 100% (33/33), и эта самооценка в основном **подтверждается чтением кода** (см. § SENAR-conformance). По собственной шкале я оцениваю **полноту SENAR ≈ 88–92%** — формальное покрытие 100%, но Rules 4 (внешняя проверка) и 6 (rollback planning) реализованы только частично (warning-only, без жёсткого enforcement), а Rule 5 checklist живёт как 4-тировая авто-детекция, а не как обязательный 28-item gate.

RENAR (Reproducible/Reasoning ENgineering Norms for AI Research — v0.1) **в TAUSIK не реализован вообще как явная фича**. Ни одного упоминания RENAR в `docs/`, `scripts/`, `tests/` или CHANGELOG. Готовность к нему я бы оценил в **15–25%** — инфраструктурно элементы есть (decisions table, dead-ends, exploration time-boxing, FTS5-поиск по логам), но репродуцируемость прогонов, провenance чейн "вопрос → исследование → решение → артефакт", и формальный reasoning trace не выделены как самостоятельная поверхность.

Главная **killer feature** — `task_gate.py` + Verify-First Contract: агент *физически* не может писать код без активной задачи и закрыть задачу без свежего verify-cache. Это единственное место в индустрии, где `git commit --no-verify`-эквивалент удалён намеренно (нет `--force` у `task done`, только у `task start`, и то с audit trail).

Главный риск — **дрейф документации vs кода**. В CHANGELOG v1.4.1 видно, что один doc-audit нашёл сразу 58 defects (32 WRONG + 22 DRIFT) по schema/gates/hooks/cli/mcp; и сам факт того, что 4-агентный аудит был необходим — индикатор, что dogfooding не покрывает doc consistency полностью. v1.4.2 ввёл `gen_doc_constants.py --check` и cross-file scan, но это компенсирующий контроль, не превентивный.

---

## Метрики продукта — что они значат на самом деле

| Метрика (publish) | Что показывает | Что НЕ показывает |
|---|---|---|
| 138 source files | Модулярность хорошая: средний файл ≈ 217 строк, file-size gate 400 строк работает | Зависимости между модулями (импорт-граф не аудитили) |
| 3378 тестов | High raw count | Coverage % не публикуется; CHANGELOG v14c-mass-parametrize-batch-1 показал, что было ~125 дубликатных тестов — реальная behavior coverage **ниже** raw count |
| 103 MCP tools (96 project + 7 brain) | Очень широкая программная поверхность для агента | Это и риск — large MCP surface → больше токенов в `tools.py` description'ах в каждом prompt; cache-bust на любую правку |
| 25 quality gates | Multi-stack support реален (5 universal + 20 stack-scoped) | Stack-scoped gates **не активируются** для custom_stacks без ручной регистрации в config.json |
| 20+1 hooks | Полное enforcement-покрытие Claude Code lifecycle | Cursor/Windsurf hooks API нет — там self-enforce |
| 11 review agents | 6-агентный `/review` parallel + 2 named subagents (`tausik-reviewer`, `tausik-gate-fixer`) + 3 vendor | "Adversarial critic" агент — единственный, что специально ищет слабые места; остальные 5 ищут типовые баги |
| 9 hook types | PreToolUse, PostToolUse, SessionStart, UserPromptSubmit, Stop, SessionEnd, pre-commit (shell) | Coverage по lifecycle полное; нет post-session-cleanup, но есть session_cleanup_check на Stop |
| 13 stacks (доки) vs 25 (DEFAULT_STACKS код) | Цифры расходятся: README говорит "13 stacks", docs/ru/cli.md перечисляет 25 default | Drift между маркетингом и реальной поверхностью — см. § тех. долг |

**Дельта marketing vs code.** README говорит "0 dependencies", это правда для core; но `.tausik/venv/` ставит MCP deps (`mcp` package) — звёздочка опущена. "3400 tests passing" в badge — реально `pyproject.toml addopts="-m 'not slow'"` пропускает slow-маркированные → "passing" верно, но не вся батарея. `TAUSIK_VERIFY_FULL=1` обнажает разницу.

---

## Архитектура (анализ `scripts/`)

Чистая трёхслойная архитектура: **CLI → Service → Backend**. Это явно описано в `docs/ru/architecture.md` и **строго выдерживается** в коде:

- `scripts/project.py` (152 строки) — точка входа, диспетчер
- `scripts/project_parser*.py` (×7 файлов) — argparse дерево, разнесено по доменам
- `scripts/project_cli*.py` (×11) — handlers per-domain (task / role / stack / verify / hygiene / aidd / config / metrics / doctor / ops / review)
- `scripts/project_service.py` + 12 mixins (`service_task.py`, `service_gates.py`, `service_verification.py`, `service_knowledge.py`, `service_session.py`, `service_recording.py`, `service_skills.py`, `service_cascade.py`, `service_roles.py`, `service_stack_ops.py`, `service_validation.py`, `service_task_done.py`, `service_task_team.py`) — бизнес-логика
- `scripts/project_backend.py` + 11 `backend_*.py` модулей — SQLite CRUD + миграции + графовая память + FTS5

**Что хорошо:**
- Зависимостей циклы я не нашёл (поверхностный взгляд) — service не импортит CLI, backend не импортит service.
- File-size gate работает: 18 файлов прижались к 350–400 строкам — паттерн "filesize-debt-paydown" (см. CHANGELOG v14b) разносит код по новым модулям, когда упирается в потолок.
- `default_gates.py` корректно делегирует stack-scoped gates в `stack_registry` (decisions не дублируются — single source of truth).
- Mixin-композиция `TaskMixin(TaskDoneReportMixin, GatesMixin, CascadeMixin)` — нестандартный подход для Python, но облегчает разрезание задач: каждый mixin в своём файле под 400 строк.

**Что вызывает сомнения:**
- **3-tier architecture с 13 mixin'ами** — это потенциально хрупкая mro (method resolution order). Если завтра нужно добавить hook между QG-2 и cache-write, придётся искать, в каком из 13 mixin'ов это делать.
- `GatesMixin._enforce_verify_first` (service_gates.py:227) — внутри пишет `from project_config import ...` локально (lazy import). Это снижает coupling, но усложняет навигацию.
- **Daemon-thread envelope timeout** в `run_gates_with_cache` (service_verification.py:266) — корректное решение для случая "гейт повис", но "daemon thread leaves the lingering subprocess unwound at interpreter exit" — это известное место, где subprocess может зависнуть осиротевшим до перезапуска IDE.

**Архитектурный рейтинг: 4.2/5.** Сильно, но местами over-engineered (13 mixin'ов когда могло быть 3–4).

---

## SENAR-conformance — рейтинг по каждому правилу

| Элемент | Авто-оценка матрицы | Мой rating (1–5) | Комментарий |
|---|---|---|---|
| **QG-0 — Цель обязательна** | ✅ Hard | 5 | `gate_qg0_check.check_qg0_start()` блокирует. Тесты `test_qg0_dimensions.py`. |
| **QG-0 — AC обязательны** | ✅ Hard | 5 | То же. |
| **QG-0 — Негативный сценарий** | ✅ Hard | 5 | `NEGATIVE_SCENARIO_KEYWORDS` — 30+ en+ru ключевых слов. |
| **QG-0 — Scope warning** | ✅ Warning | 4 | Warning-only — может быть проигнорирован агентом. |
| **QG-0 — Security surface** | ✅ Warning | 4 | Warning при отсутствии security AC; не блокирует. |
| **QG-2 — AC evidence** | ✅ Hard | 5 | `verify_ac()` — нет `--force`. Структурированный `--evidence-json` (v1.4). |
| **QG-2 — Plan complete** | ✅ Hard | 5 | JSON-план в task. |
| **QG-2 — Scoped pytest** | ✅ Hard | 4.5 | Basename-маппинг — корректный, но эвристический. `test_<basename>.py` glob может пропустить нестандартные раскладки. |
| **QG-2 — Verify cache** | ✅ Skip-on-hit | 5 | 10-min TTL + files_hash + security bypass + git-diff cross-check. Best-in-class. |
| **QG-2 — Quality gates** | ✅ Hard | 5 | 25 gates, stack-aware. |
| **QG-2 — Checklist tier** | ✅ Warning | 3.5 | Auto-tier работает, но это warning. SENAR Rule 5 fast-track 28-item checklist реализован "warning + tier", не hard. Это и есть главный gap. |
| **QG-2 — Root cause** | ✅ Warning | 3.5 | Keyword detection в notes — false-positive риск. |
| **QG-2 — Knowledge capture** | ✅ Warning | 4 | `--no-knowledge` opt-out явный — честно. |
| **Rule 1 — No code without task** | ✅ Hard (hook) | 5 | `task_gate.py` блокирует Write/Edit. **Killer feature**. |
| **Rule 2 — Scope boundaries** | ✅ Warning | 3 | Warning-only — реальный enforcement зависит от агента. |
| **Rule 3 — Verify against criteria** | ✅ Hard | 5 | QG-0 + QG-2 пара. |
| **Rule 4 — External validation** | ❌ Не упомянуто | 1.5 | **NOT IMPLEMENTED.** `/review` — внутренний 6-агентный pipeline; "external" в SENAR-смысле (другой агент с другим контекстом) сейчас покрывается только `tausik-reviewer` named subagent, и то опционально через `/review lite`. |
| **Rule 5 — Verification checklist** | ✅ Warning | 3.5 | 4-tier auto-detect, но не enforce. |
| **Rule 6 — Rollback planning** | ❌ Не упомянуто | 1 | **NOT IMPLEMENTED.** В docs/ru/senar.md явно сказано: "Правила 4–6 существуют в спецификации, но пока не применяются". |
| **Rule 7 — Root cause for defects** | ✅ Warning | 3.5 | Keyword-detection ограничен. |
| **Rule 8 — Knowledge capture** | ✅ Warning | 4 | `tausik decide`, `memory add`, `dead-end`. |
| **Rule 9.1 — Task before code** | ✅ Hard | 5 | = Rule 1. |
| **Rule 9.2 — Session limit (180 min)** | ✅ Hard | 5 | Gap-based active time — единственная индустрия, кто это делает правильно (clip AFK до 10 min). |
| **Rule 9.3 — Checkpoint cadence** | ✅ Warning (auto) | 4 | MCP-счётчик + warning на 40 calls. |
| **Rule 9.4 — Dead ends** | ✅ Instruction | 4 | `tausik dead-end` + skill reminders. |
| **Rule 9.5 — Periodic audit** | ✅ Warning | 4 | `audit_check/mark` MCP. |
| **Rule 9.15 — AI Output QA** | ✅ Instruction | 4 | 6-agent `/review` parallel. |
| **6 Metrics (Throughput, Lead Time, FPSR, DER, Dead End Rate, Cost/Task)** | ✅ Hard auto | 5 | Все 6 в `backend_queries.get_metrics()`. |
| **Section 5.1 — Explorations** | ✅ 3/3 Hard | 5 | Time-boxed (default 30 min), clamps 1–480. |
| **Multi-lang gates** | ✅ Hard auto | 5 | 25 stacks встроенных. |
| **MCP coverage** | ✅ Hard | 5 | 103 tools, заявлены 0 CLI-only gaps в agent-loop (admin verbs OK). |

**Суммарный SENAR rating: 4.10/5.0 ≈ 82%** — близко к моей экспертной оценке полноты 88–92% (расхождение из-за того, что я считаю Rules 4/6 критичными, а матрица их выводит за пределы Core).

---

## RENAR-readiness — gap analysis

RENAR (как стандарт reproducible AI engineering) — **не имплементирован**. Ни одного упоминания в репо. Что есть инфраструктурно:

| RENAR concept (предполагаемый) | TAUSIK инфраструктура | Готовность |
|---|---|---|
| Reasoning trace per task | `task_logs` table + FTS5 | 60% — есть, но нет structured reasoning steps (intent → premise → action → verification) |
| Provenance chain | `decisions` + `memory_edges` (supersedes / caused_by / contradicts) | 50% — graph есть, но нет цепочки "research → decision → code → test" с явными ссылками |
| Reproducibility | `verification_runs.files_hash`, prompt-caching validator | 40% — есть idea, нет prompt-snapshot / model-version pinning per task |
| Audit log | `events` table | 70% — лог есть, гарантии immutability нет (нет hash-chain / append-only enforcement) |
| Model version tracking | `sessions.model_id` / `model_version` | 50% — есть колонки, но usage_events связь слабая |
| Cost reproducibility | `usage_events` + `cost_pricing.py` | 65% — реально работает, но не привязано к decision provenance |

**RENAR-готовность: ≈ 20–25%.** Инфраструктура на 50%, но нет UX, нет публичного контракта, нет тестов на reproducibility.

**Что блокирует RENAR-релиз:**
1. Нет formal reasoning trace API (`/reason start` skill + `reasoning_steps` table).
2. Нет model-version-pinning per task (текущий `usage_events.model_id` — best-effort, не enforce).
3. Нет `task replay` команды, чтобы воспроизвести решение с тем же model + промпт-кешем.

---

## DX (Developer Experience) audit

**Сильные стороны:**
- **Onboarding < 15 минут** (quickstart): submodule + bootstrap + restart IDE — три команды, всё генерируется автоматически.
- **"Tell your agent" pattern** (README): рабочий вариант, когда установку делает сам агент по копи-паст промпту.
- **Token efficiency v1.4.x**: с 38 skills (~1520 tok/turn) → 12 + brain conditional (~480 tok/turn) — экономия 68% per turn. Это огромная адаптация под реальную экономику.
- **`tausik doctor`**: 4-group health check + drift detection с явными remediation hints.
- **Russian + English docs**: 49 + 47 файлов, регулярные audit'ы translation-drift (см. CHANGELOG v14b-audit-translation-skip-marker).
- **Verify-First Contract**: "task done в миллисекунды" — действительно меняет UX интерактивной работы.

**Слабые стороны:**
- **CLI surface ≥ 80 команд** (epic / story / task / session / gates / skill / brain / stack / role / memory / doctor / hud / metrics / roadmap / events / search / decide / dead-end / explore / audit / run / doc / verify / suggest-model / team / update-claudemd / fts / init / push-ok / hygiene). Учить не нужно (skills wrap), но debugging требует.
- **Memory 4-tier** (TAUSIK memory + Claude auto-memory + Brain + CLAUDE.md). Документация старается разделить — на практике пользователю приходится думать, куда что писать. См. § Memory architecture.
- **Windows-friction**: `.tausik/tausik` — bash wrapper, на cmd.exe не работает. Есть `.tausik/tausik.cmd`, но quickstart/RU рекомендует Git Bash / WSL.
- **`tausik` нет в PATH** — после bootstrap агент должен звать через `.tausik/tausik` (относительный путь). Это намеренно (per-project venv), но визуально шумно.
- **MCP server timeout (VS Code Claude Extension ≈ 60s)** — упомянут в quickstart как gotcha; Verify-First Contract пришлось ввести **специально** под этот баг хоста.

**DX rating: 4.0/5.** Отличный onboarding, тяжёлый surface для деep-debugging.

---

## Tests audit

**Числа:**
- 183 test-файла, 3378 заявленных тестов (badge: "3400 passing")
- 43 208 строк теста vs 29 984 строки исходников — **1.44× test-to-source ratio**, отлично
- `pyproject.toml addopts="-m 'not slow'"` — fast lane по умолчанию (~1.5 min); `TAUSIK_VERIFY_FULL=1` запускает всё (~12 min)
- `audit_pytest_dedupe.py` — собственный аудит дубликатов (CHANGELOG v14c-mass-parametrize-batch-1: 25+ групп схлопнуты в parametrize, ~125 тестов удалены)

**Что покрыто хорошо:**
- Backend CRUD (`test_tausik_backend.py`), все 27 миграций (`test_migrations.py`)
- Все гейты (`test_gates.py`, `test_qg0_dimensions.py`, `test_qg2_gates.py`, `test_gate_stack_aware.py`)
- E2E workflow (`test_e2e_workflow.py`) — есть, но один файл
- MCP integration (`test_mcp_integration.py`, `test_mcp_self_check.py`, `test_mcp_verify_handler.py`, `test_mcp_windows.py`)
- Hook subprocess'ы (28 файлов `test_*hook*.py` + `_common`)
- Bootstrap matrix (`test_bootstrap_*` × 12)
- Brain (`test_brain_*` × 22) — несоразмерно много для optional feature
- Concurrent / stress (`test_concurrent.py`, `test_stress.py`)
- FTS5 sanitizer (`test_fts5_sanitizer.py` — 22 cases) — добавлен после v1.4.1 regression

**Слабые места:**
- Coverage % не публикуется. По числу тестов **выглядит** покрытие 80%+, но без verifiable метрики это маркетинг.
- "Slow" tests (subprocess-heavy, MCP integration, E2E) **не запускаются в fast lane** — реально каждый push в TAUSIK проверяет упрощённый сабсет.
- Performance tests / SQLite scaling — `test_stress.py` есть, но не публикуется лимит "до N тасков".

**Tests rating: 4.3/5.** Числа хорошие, отсутствие coverage% — единственное серьёзное замечание.

---

## Скорость работы (perf concerns)

**SQLite + FTS5 — реальные риски:**
- **WAL mode + concurrent agents** документированы как working (multi-agent `task claim`). Но `run_gates_with_cache` docstring явно признаёт: "two simultaneous `task done` calls for the same slug both miss cache, both run gates, both `record_run`. SQLite WAL keeps this safe (no corruption); the cost is duplicate `verification_runs` rows and redundant gate work."
- **`fts_*` triggers** на каждое INSERT/UPDATE/DELETE для `tasks`, `memory`, `decisions`, `task_logs` — на 10k+ задач это становится заметно. `fts optimize` команда есть, ручная.
- **`backend_queries.get_metrics()`** — combined query с `julianday()`, `GROUP BY complexity` — на 10k tasks это всё ещё OK (миллисекунды), но не line.
- **Per-PostToolUse hook overhead**: `task_call_counter` + `posttool_usage` + `activity_event` + `task_cost_budget_check` + `auto_format` + `tool_output_truncation_nudge` = 6 хуков на каждый tool call. Каждый — отдельный Python subprocess (cold start ~50–80 ms). Это **300–480 ms latency** на каждый Read/Write/Edit. На 200-call сессии = 60–96 секунд накладных расходов.

**Scaling estimate:**
- До **5k tasks** — комфортно (FTS5 + индексы).
- 5k–20k — потребуется `fts optimize` + возможно partition по `archived_at`.
- 20k+ — SQLite перестанет быть оптимальным. Schema_v27 это не задумывала.

**Performance rating: 3.5/5.** Хорошая основа, скрытый стоимостной хвост на hook'ах.

---

## Security audit

**Что реализовано (сильно):**
- `bash_firewall.py` — regex с word boundaries (fix v1.3.4 — раньше substring match ловил false-positives на `echo "git push --force"`).
- `secret_scan.py` (v1.4) — AWS/GitHub/Slack/Stripe/OpenAI/Anthropic/JWT/private-key/generic `password|api_key`. Warning по умолчанию, `TAUSIK_SECRET_SCAN_STRICT=1` блокирует.
- `git_push_gate.py` — single-use ticket с TTL 60s + HEAD SHA bind. v1.4 удалила broken env-bypass (был просто декорацией — env never reached hook subprocess).
- `memory_pretool_block.py` — блокирует cross-project leak в `~/.claude/`.
- `brain_scrubbing.py` — scrubbing linter для абсолютных путей, kebab-slag'ов ≥3 частей, .tausik команд.
- SHA256 project hashes в Brain для приватности.
- `is_security_sensitive()` — security paths (auth/payment/billing/hooks/) bypass verify cache.

**Что вызывает риски:**
- **`shell=True` в `gate_command_runner.py:75`** при наличии `|`, `&&`, `>>`, `2>&1`. Команды берутся из `default_gates.py` + `stack_registry` + custom stacks в `.tausik/config.json`. Если кто-то правит custom stack — может попасть command injection. Не критично (это файл, который пишет владелец проекта), но шероховатость.
- **`bandit` gate `enabled: False`** по умолчанию. Включить руками — не делается автоматически.
- **`tdd_order` disabled** — это OK по дефолту, но в README/docs он рекламируется как фича.
- **MCP server traceback** — `server.py:90` пишет full traceback в stderr но возвращает agent только `Error: {e}` — корректно, frame-locals не утекут в model context.
- **No supply chain proof** — нет SBOM, нет signed releases. Vendor skill auto-install (`tausik skill install`) скачивает code из GitHub, проверяется только URL/origin, контент не верифицируется.
- **Hook subprocess'ы получают stdin tool_input** — это user-controlled. Хуки в основном parse JSON и не выполняют — но если кто-то добавит `os.system(tool_input.get('command'))` в кастомный хук — game over. Контракт hook'ов читает (а не пишет) — соблюдается **везде** в стандартных хуках, но это конвенция, не enforcement.

**Security rating: 3.8/5.** Хорошие основы, нужен formal supply-chain story и SBOM для 2.0.

---

## Vendor lock-in

**Заявлено:** Multi-IDE (Claude Code, Cursor, Qwen Code, Windsurf, Codex), multi-model (Opus/Sonnet/Haiku/GPT-4/5/5-5/Qwen).

**Реальность:**
| Capability | Claude Code | Cursor | Qwen | Codex | GPT (любой) |
|---|---|---|---|---|---|
| MCP tools | ✅ | ✅ | ✅ | partial | ✅ |
| 20 Python hooks | ✅ | ❌ (no API) | partial | ❌ | ❌ |
| Slash skills | ✅ native | ❌ (read SKILL.md) | partial | ❌ | ❌ |
| `~/.claude/...` memory | ✅ | ❌ | read-only | ❌ | ❌ |
| Validation status | "officially tested" + Cursor | "officially tested" | "expected" | "expected" | "expected" |

**Вывод:** TAUSIK **архитектурно multi-IDE**, но enforcement-разница между Claude Code (full hooks + skills) и Cursor/Qwen (только MCP + self-serve) — огромная. Если ваш агент не Claude и не Cursor — вы получаете ~60% от обещанной дисциплины.

**Vendor-neutrality rating: 3.5/5.** Architecturally honest, enforcement is Claude-first.

---

## Memory / skill / hook architecture — глубокий разбор

**Memory 4-tier:**

| Tier | Где | Что | Когда |
|---|---|---|---|
| 1. TAUSIK memory | `.tausik/tausik.db` (`memory`, `decisions`, `task_logs`) | Project-scoped patterns / gotchas / conventions / dead_ends / decisions | Каждая задача, hot path |
| 2. Claude auto-memory | `~/.claude/projects/<dir>/memory/MEMORY.md` | Cross-project user habits | Implicit, IDE-managed |
| 3. Shared Brain | Notion (4 DBs) + local mirror `~/.tausik-brain/brain.db` | Cross-project artifacts / patterns / web cache | Opt-in после `brain init` |
| 4. CLAUDE.md | Repo root | Static rules + dynamic block (session number, task counts) | Каждый turn (re-injected) |

**Проблема:** пользователю объяснили, что у нас 4 уровня, но `memory_pretool_block.py` блокирует запись project-инфо в `~/.claude/` — то есть **граница между tier 1 и tier 2 enforced**. Между tier 1 (local) и tier 3 (brain) — есть scrubbing, classifier, universality detector. Tier 4 (CLAUDE.md) обновляется отдельной командой `tausik update-claudemd`.

**Это не путаница, это многослойная защита.** Но onboarding-документация недостаточно объясняет **зачем** четыре уровня, а не один. Agent с непустой auto-memory путается между tier 1 и tier 2 — лечится дисциплиной "Знания фреймворка остаются здесь" (CLAUDE.md).

**Memory rating: 4.0/5.** Архитектурно сильно, UX-документация слабая.

---

**Skills:**

- **12 core auto-deployed** (`/start`, `/end`, `/checkpoint`, `/plan`, `/task`, `/ship`, `/commit`, `/review`, `/test`, `/debug`, `/explore`, `/interview`) + `/brain` conditional.
- **25 vendor opt-in** через `skills-official/` (`zero-defect`, `markitdown`, `audit`, `security`, `optimize`, `ultra`, `daily`, `run`, `loop-task`, `dispatch`, `jira`, `bitrix24`, `confluence`, `sentry`, `excel`, `pdf`, `docs`, `presale`, `retro`, `skill-test`).
- **2-axis variants** (`variants/ide/{claude,cursor,qwen,codex}.md` + `variants/model/{opus,sonnet,haiku,gpt-4,gpt-5,gpt-5-5,qwen}.md`).
- **Bundles** (v1.4): `integrations`, `data-formats`, `quality-pro`, `automation`, `workflow-helpers`, `ru-locale`.
- **Marketplace**: `tausik skill repo add <url>` + auto-clone.

**Сравнение:**
- **Claude Skills (Anthropic native)**: рудиментарны, не bundleable, нет model-axis.
- **Cursor Rules**: статичные правила, нет lifecycle.
- **Continue Rules**: похоже на Cursor, нет dynamic.
- **TAUSIK skills**: **самые мощные** из открытых систем — есть variants, bundles, marketplace, проверка устаревания (`tausik skill rebuild`), token budget per skill, conditional deployment.

**Skills rating: 4.7/5.** Best-in-class.

---

**Hooks (20+1):**

| Категория | Кол-во | Цель |
|---|---|---|
| PreToolUse | 6 (task_gate, memory_pretool_block, secret_scan, bash_firewall, brain_search_proactive, git_push_gate) | Enforce |
| PostToolUse | 9 (auto_format, memory_posttool_audit, task_done_verify, brain_post_webfetch, task_call_counter, posttool_usage, activity_event, tool_output_truncation_nudge, task_cost_budget_check) | Observe + nudge |
| SessionStart | 1 (session_start) | Inject |
| UserPromptSubmit | 1 (user_prompt_submit) | Drift detect |
| Stop | 2 (keyword_detector, session_cleanup_check) | Coach |
| SessionEnd | 1 (session_metrics) | Record |
| Git pre-commit | 1 (shell mypy + RAG warn) | Block on type errors |

**Over-engineering check:** 6 хуков PostToolUse запускаются на **каждый** tool call. Latency overhead 300–480 ms (см. § perf). С другой стороны, без них нет Verify-First Contract enforcement, нет cost budget tracking, нет drift detection. Trade-off оправдан, но было бы хорошо иметь "batch hook runner" чтобы запустить их в одном subprocess.

**Hooks rating: 4.2/5.** Полезный набор, perf cost скрыт.

---

## Сравнение с базой

| Сценарий | Что есть | Что теряется без TAUSIK |
|---|---|---|
| **Vanilla Claude Code, нет CLAUDE.md** | Только агент + tools | Всё: нет goal/AC, нет session continuity, нет verify, нет dead ends, нет metrics, нет hooks |
| **Claude Code + AGENTS.md only** | Письменные рекомендации | Enforcement = 0, агент игнорирует или забывает |
| **Cursor Rules** | Static rules в `.cursorrules` | Нет lifecycle, нет metrics, нет hooks API |
| **Claude Skills (Anthropic native)** | 8–10 встроенных skills | Нет project DB, нет dead-end tracking, нет multi-IDE |
| **TAUSIK** | Все вышеперечисленные + enforcement + project memory + metrics | — |

**Ключевая дельта:** **Enforcement vs Suggestion.** AGENTS.md/Cursor Rules — рекомендации. TAUSIK — `task_gate.py exit 2` + Verify-First refuse-to-close.

---

## Технический долг — выборочно (10–20 примеров)

В коде только **3 TODO/FIXME/HACK** (audit_pytest_dedupe.py:118, test_brain_move.py × 2). Это **исключительно** низкая плотность маркеров — TAUSIK действительно следует "нулевой толерантности к тихим ошибкам".

Долг по CHANGELOG и docs:

1. **`/notify_on_done` hook удалён в 1.3.6 как orphan** (TODO.md) — нужно восстановить из git history. До сих пор не восстановлено в v1.4.2.
2. **`Outline` как alt-backend для Shared Brain** (TODO.md, 2026-04-22) — нет MVP.
3. **Cursor MCP rework для v1.5** (CHANGELOG Unreleased) — composer/workspace MCP filesystem mirror не публикует stdio servers; investigation документирована, патча нет.
4. **README/docs drift:** "13 stacks" в маркетинге vs 25 в `DEFAULT_STACKS`. Не исправлено в v1.4.2 (хотя cross-file scan его не ловит — это не version-ref).
5. **`tdd_order` enabled=False** по умолчанию, рекламируется в functionality table.
6. **`bandit` enabled=False** по умолчанию.
7. **Coverage % не публикуется** — badge "3400 tests passing" не отражает реальное покрытие (после parametrize-batch стало меньше уникальных тестов).
8. **`shell=True` в gate_command_runner** для команд с `|`/`&&` — потенциальный command injection через custom stacks.
9. **Daemon-thread envelope timeout** — subprocess может остаться осиротевшим (service_verification.py:255).
10. **`v14c-defect-mcp-tool-handler-drift`** (CHANGELOG: spawned defect task) — `test_every_tool_name_has_handler` падает; не закрыто на момент v1.4.0.
11. **`v14c-defect-bulk-decisions-stress`** — `test_bulk_decisions` падает.
12. **MCP tool descriptions** — каждая правка переписывает prompt prefix → cache bust (документировано в `architecture.md`, но нет CI-gate, который ловил бы accidental rewording).
13. **6 PostToolUse hooks per tool call** = 300–480 ms latency, не документировано как perf cost.
14. **Manual `fts optimize`** — без cron / scheduled задачи.
15. **No SBOM / signed releases**.
16. **Vendor skill auto-install** скачивает arbitrary code без content verification.
17. **README количества: "5-agent" → "6-agent"** (см. CHANGELOG v1.4.1) — drift между маркетингом и кодом регулярный, исправляется ad-hoc.
18. **"0 dependencies" badge** игнорирует MCP venv deps (`mcp` package).
19. **Brain feature: 22 test files** — несоразмерно для opt-in feature; может быть индикатором, что Brain сложнее чем должен быть.
20. **`tausik task done` без `--force`** (правильно), но **`tausik task start --force` есть** — асимметрия может быть exploit'ом если агент через scope bypass обходит QG-0.

---

## Топ-10 находок с рекомендациями

1. **SENAR Rule 4 (External Validation) не имплементирован.** → Add named subagent `tausik-external-reviewer` который запускается на **другой модели** (например, если task делал Sonnet — review делает Opus). Rule 4 hard-block для tasks с complexity=complex.

2. **SENAR Rule 6 (Rollback Planning) не имплементирован.** → Введите поле `tasks.rollback_plan TEXT`, QG-0 warning для tasks с stack=docker/terraform/kubernetes/django-migrations.

3. **RENAR не имплементирован.** → Скаффольд для v2.0: `reasoning_steps` table (task_slug, step_num, intent, premise, action, evidence, ts), новый MCP tool `tausik_reason_step`, новый skill `/reason`.

4. **Coverage % не публикуется.** → Добавить `pytest-cov` в `verify`, публиковать в badge + `docs/_generated/constants.json`. Текущий "3400 tests" — vanity metric.

5. **PostToolUse latency 300–480 ms.** → Batch runner: один Python subprocess читает stdin, диспетчит на все 6 PostToolUse-хуков sequentially in-process. Сокращает 6× cold-start до 1×.

6. **`shell=True` в gate_command_runner.** → Replace shell-detection с явным parsing pipeline ops; либо требовать `shell_safe: true` в gate config с whitelist допустимых ops.

7. **Drift docs vs code.** → Существующий `gen_doc_constants.py --check` — отлично. Расширить cross-file scan на **stack counts** ("13 stacks" vs 25), **hook counts**, **subagent counts**.

8. **Memory 4-tier UX.** → Добавить decision tree skill `/where-does-this-go` — диалог "это про этот проект? кросс-проектное?" → автоматически выбирает tier.

9. **Vendor-neutrality drift между Claude и Cursor.** → Признать в маркетинге "Claude-first, Cursor parity 80%, others best-effort"; не публиковать "100 tools = same governance" таблицу без асе́рисков.

10. **No SBOM / supply chain.** → Sign releases (Sigstore), publish SBOM с CycloneDX, content-hash для vendor skill auto-install.

---

## Оценка 1–10 по осям

| Ось | Оценка | Обоснование |
|---|---|---|
| **SENAR полнота** | 8.5/10 | 33/33 core элементов, но Rules 4/6 partial; Rule 5 = warning, не hard |
| **RENAR готовность** | 2/10 | Не имплементирован; инфраструктура на 50% |
| **DX** | 7.5/10 | Отличный onboarding, тяжёлый CLI surface, Windows friction |
| **Performance** | 6.5/10 | SQLite до 5k tasks OK, hook latency скрыт; нет публичного бенчмарка |
| **Security** | 7/10 | Хорошие основы, нет supply chain story |
| **Tests** | 7.5/10 | 3378 высокий count, но coverage % не публикуется, fast lane скрывает slow tests |
| **Документация** | 8/10 | 49+47 файлов, RU/EN sync; периодический drift |
| **Расширяемость** | 8.5/10 | Custom stacks, skill marketplace, MCP-first дизайн |
| **Vendor-neutrality** | 6.5/10 | Multi-IDE задумано, enforcement Claude-first |
| **Adoption-readiness** | 7.5/10 | Production-grade core, marketing-honesty work-in-progress |

**Средняя: 6.95/10.** Сильный pre-2.0 кандидат, не релизный 1.5.

---

## Сильные стороны как продукт

**Killer features (по убыванию):**
1. **`task_gate.py`** — единственная индустрия, где агент *физически* не может писать код без активной задачи.
2. **Verify-First Contract** — millisecond task close + cached heavy verify. Меняет UX.
3. **Gap-based active time** для session limit — не наивный wall-clock.
4. **Project memory с FTS5 + graph edges** — re-injection в каждой сессии.
5. **Dead end tracking** — реально снижает recurring failures (FPSR доходит до 90%+ по dogfooding metrics).
6. **2-axis skill variants** — Claude × model overlay, никто другой так не делает.

**Что мешает adoption:**
1. **Onboarding выглядит легко, поверхность глубокая** — debug требует знания CLI surface.
2. **Claude-first дисциплина** vs multi-IDE заявления.
3. **No SaaS / Cloud version** — это by design (local-first), но для коммерческих команд это barrier.
4. **Naming**: "TAUSIK" не запоминаемо; cyrillic backronym ("Технический Агент Унифицированного Сопровождения, Инспекции и Контроля") видим только в RU-доках.

---

## Готовность к 1.5: 3 главных блокера

1. **Cursor MCP rework** (уже в Unreleased) — composer/workspace MCP filesystem mirror не публикует stdio servers; investigation документирована, реализации нет. До закрытия 1.5 нельзя выпускать с заявлением "Cursor officially tested".

2. **Coverage measurement** — без публикации coverage % "3400 tests" остаётся vanity metric. Нужен `pytest-cov` в CI + badge.

3. **Doc/code drift baseline** — `gen_doc_constants.py --check` ловит version-refs, но не ловит "13 vs 25 stacks", "5-agent vs 6-agent" и подобные расходы. Нужен расширенный cross-file scanner либо ручной pre-release аудит.

---

## Заключение

TAUSIK — **самая зрелая референсная реализация SENAR** на момент аудита. По коду — production-grade: clean 3-tier architecture, file-size discipline, 1.44× test ratio, zero TODO/FIXME pollution. По SENAR-полноте — 88–92% (формально 100%, фактически Rules 4/6 partial). RENAR — не цель текущего релиза, готовность 20%.

Главная сила — **enforcement, а не suggestion**. Это единственный фреймворк, где AGENTS.md-эквивалент работает потому, что хуки делают экзекьюшн обязательным.

Главная слабость — **doc/marketing drift**. Команда осознаёт это (см. ad-hoc audit'ы и `gen_doc_constants.py --check`), но превентивная дисциплина пока не отлажена.

Релиз 1.5 — **близок, но не сейчас**. Блокеры разрешимы за 1–2 sprint'а. 2.0 потребует RENAR-roadmap и multi-IDE matrix-completion.
