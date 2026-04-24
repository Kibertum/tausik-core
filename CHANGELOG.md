# Changelog

All notable changes to this project will be documented in this file.

This project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased] — Shared Brain pipeline

Cross-project knowledge layer backed by Notion, complementing the per-project `.tausik/tausik.db`. Only knowledge flagged as *generalizable* reaches the brain; project-specific traces stay local. Read-path fully implemented and offline-tested end-to-end; write-path and MCP tooling are the next story. 6 tasks done from epic `shared-brain` / 22 total. Кросс-проектный слой знаний на базе Notion.

### Added / Добавлено

- **Design doc** ([references/brain-db-schema.md](references/brain-db-schema.md)) — full spec of 4 Notion databases (`decisions`, `web_cache`, `patterns`, `gotchas`): property types + obligation, JSON `pages.create` payload for each, delta-pull mechanics (`last_edited_time` high-water mark), rate-limit handling, 7 trade-offs discussed, 8 negative-scenario fallbacks, privacy model (`SHA256(project_name_canonical)[:16]`) — Design-doc, без которого остальные задачи бы плавали
- **Local SQLite mirror** ([scripts/brain_schema.py](scripts/brain_schema.py)) — 4 tables mirroring Notion properties 1:1, FTS5 virtual tables with `unicode61 remove_diacritics 2` tokenizer (Cyrillic works), AI/AD/AU triggers per table, CHECK constraints for `generalizable` / `confidence` / `severity` / `sync_state.category`, 13 indexes covering delta-pull and dedup hot paths — Локальное FTS5-зеркало с поддержкой кириллицы
- **Brain config section** ([scripts/brain_config.py](scripts/brain_config.py)) — `DEFAULT_BRAIN` with safe defaults (enabled=false, mirror path, token env name, empty db-ids), `load_brain` / `is_brain_enabled` / `validate_brain` (returns error list, strict only when enabled=true) / `get_brain_mirror_path` (expands `~` and `$ENV`) / `compute_project_hash` (canonicalize then SHA256[:16]). Token is never stored in config — only the env-var name — Секция конфига с приватностью
- **Notion REST client** ([scripts/brain_notion_client.py](scripts/brain_notion_client.py)) — stdlib-only (urllib + http), zero external deps. Public API: `pages_create` / `pages_retrieve` / `pages_update` / `databases_query` / `iter_database_query` (auto-pagination iterator) / `search`. Write-side throttle 350 ms, 429/5xx retry with `Retry-After` and exponential backoff (2^n ± 20% jitter, cap 30 s), auth/not-found bypass retry, injected `urlopen`/`clock`/`sleep` for deterministic tests — REST-клиент без внешних зависимостей
- **Pull-sync engine** ([scripts/brain_sync.py](scripts/brain_sync.py)) — `open_brain_db` (creates parent dir, applies schema), per-category mapper (Notion `title`/`rich_text`/`multi_select`/`select`/`date`/`checkbox`/`url`/`number` → SQLite columns), `upsert_page` (INSERT OR REPLACE by `notion_page_id`), `sync_category` (delta filter by `last_pull_at`, ascending sort, advances high-water mark, records `last_error` on failure and re-raises), `sync_all` (continues after a single-category failure) — Делта-синк Notion → local
- **Local FTS5 search** ([scripts/brain_search.py](scripts/brain_search.py)) — `sanitize_fts_query` (neutralizes FTS5 operators via phrase-quoting; escapes inner `"` as `""`), `search_local` (bm25 ranking, global sort across 4 categories, `limit`/`offset`, category filter), `get_by_id` (exact lookup), SQL `snippet()` with `[...]` markers — Быстрый поиск по локальному зеркалу
- **Docs** — EN [docs/en/shared-brain.md](docs/en/shared-brain.md) and RU [docs/ru/shared-brain.md](docs/ru/shared-brain.md): philosophy (generalizable only), ASCII architecture diagram, manual setup steps (parent page → 4 databases → integration → token env → config → smoke-test), privacy contract, 7-row edge-cases table covering revoked token / rate-limit / offline / oversized content / scrubbing miss / schema drift / hash collision. README EN/RU have a short "Shared Brain" section linking to docs — Документация EN/RU + секции в README
- **PostToolUse WebFetch auto-cache hook** ([scripts/hooks/brain_post_webfetch.py](scripts/hooks/brain_post_webfetch.py)) — парный к PreToolUse `brain_search_proactive`: каждый успешный `WebFetch` автоматически уходит в `brain_web_cache` через `brain_mcp_write.store_record`, так что следующий fetch того же URL блокируется читающим хуком. Non-blocking (exit 0); пропускает приватные URL (`brain.private_url_patterns`), HTTP ≥ 400, пустые ответы, уже-свежие URL в зеркале, использует `response.url` вместо `input.url` после редиректа, обрезает content по 200 KB и stdin по 1 MiB. Scrubbing-блоки (private_urls / project_names_blocklist) тихо скипятся — это ожидаемое поведение, а не баг. Диагностика через `TAUSIK_BRAIN_HOOK_DEBUG=1`. `WebSearch` намеренно не кэшируется: в ответе несколько URL в одном блобе, нет канонического ключа; поисковые запросы обслуживаются FTS5 по контенту, записанному через `WebFetch` — PostToolUse хук для auto-cache web результатов
- **Brain runtime write helper** ([scripts/brain_runtime.py](scripts/brain_runtime.py)) — `try_brain_write_web_cache(url, content, cfg, *, query, title)` повторяет контракт `try_brain_write_decision`: `(True, page_id)` на `ok`/`ok_not_mirrored`, `(False, reason)` на token missing / scrub block / notion error / exception. Используется хуком и будущими callers (brain-skill-ui). Также выделен shared `_format_scrub_detectors` — surface только detector names, никогда raw `match` — Раннтайм-хелпер записи web_cache
- **Shared brain-hook utilities** ([scripts/brain_hook_utils.py](scripts/brain_hook_utils.py)) — `parse_iso_to_epoch`, `lookup_exact_url`, `is_fresh` вынесены из `brain_search_proactive.py`, чтобы пара Pre+Post хуков WebFetch делила одну реализацию mirror-lookup и TTL-семантики. `lookup_exact_url` корректно разбирает смешанные ISO-форматы (`Z` vs `.000Z`) — сортирует по parsed epoch, а не лексикографически по TEXT — Общие хелперы для brain-хуков
- **Hook registration** — `bootstrap_generate.py` регистрирует `brain_post_webfetch.py` на PostToolUse с matcher=`WebFetch`, timeout=10s. PreToolUse matcher `WebSearch|WebFetch` остался за `brain_search_proactive.py` — Регистрация в bootstrap
- **`/brain` skill** ([agents/skills/brain/SKILL.md](agents/skills/brain/SKILL.md)) — conversational UI над brain MCP tools: `/brain query <text>` → `brain_search`, `/brain store <type> <text>` → `tausik decide` или `brain_store_*`, `/brain show <id> <category>` → `brain_get`. Документирует bypass-маркеры (`refresh: web_cache`, `confirm: cross-project`), поведение при disabled brain, правила scrubbing. Не изобретает tool names — каждая подкоманда мапится на существующий MCP tool или CLI. `move` и `status` подкоманды вынесены в follow-up tasks `brain-skill-move` + `brain-skill-status` (нужны новые backend'ы) — `/brain` skill для query/store/show
- **`brain_runtime.open_brain_deps()`** ([scripts/brain_runtime.py](scripts/brain_runtime.py)) — shared `(conn, client, cfg)` primitive с None-семантикой: `(None, None, cfg)` если brain disabled, `(conn, None, cfg)` если token env unset, `(conn, client, cfg)` happy path. Fold: `_open_deps` + `_build_client` удалены из `agents/claude/mcp/brain/handlers.py` и `agents/cursor/mcp/brain/handlers.py` — оба импортируют из brain_runtime. Устраняет дубликат ~20 строк × 2 файла. Также добавлен `_FAST_FALLBACK_TIMEOUT = 5.0` как shared константа — Общий helper setup'а brain-зависимостей

### Test Coverage / Тесты

- **+102 new tests** — `test_brain_schema.py` (17), `test_brain_config.py` (20), `test_brain_notion_client.py` (26), `test_brain_sync.py` (15), `test_brain_search.py` (24). Entire brain-suite green in 2 s; no network I/O (client tests inject `_Recorder`/`_ClockSleep`). Pre-existing 918 tests unaffected.

### Knowledge Captured / Накоплено знаний

- **Decision #30** — 4 Notion databases, not one flat table (UX outweighs sync overhead)
- **Decision #31** — `SHA256(canonical)[:16]` privacy hash (64 bits, no plaintext project names)
- **Decision #32** — separate `Content Hash` column for `web_cache` dedup (URL changes over time)
- **Decision #33** — inject `urlopen` / `clock` / `sleep` via constructor instead of global monkeypatch
- **Gotcha #34** — FTS5 MATCH treats `-` as column-qualifier; wrap queries in `"..."` or avoid hyphens in markers
- **Convention #35** — `brain-*` modules are separate files (`brain_config.py`, `brain_schema.py`, ...), never folded into `project_config.py` — the 400-line file limit is real

## [1.3.0] — 2026-04-23

### Memory-Discipline Epic — auto-memory protection

Protects Claude's cross-project auto-memory (`~/.claude/projects/*/memory/`) from accidental project-specific writes. Project knowledge belongs in TAUSIK's per-project SQLite store (`tausik memory add`); the user's home memory is for cross-project preferences only. 8 tasks shipped across 3 stories. Защита Claude auto-memory от случайного проектного контекста.

### Added / Добавлено

- **PreToolUse memory block** (`scripts/hooks/memory_pretool_block.py`) — blocks Write/Edit/MultiEdit to `~/.claude/projects/*/memory/` from any TAUSIK project with a guidance message. Bypass via the `confirm: cross-project` marker in the user's latest prompt — hook parses the Claude Code transcript JSONL, honors both flat-string and list-of-content-blocks message shapes, and skips tool_result turns when finding the real user message — Блокирует записи в auto-memory с escape-маркером для кросс-проектных случаев
- **PostToolUse memory audit** (`scripts/hooks/memory_posttool_audit.py`) — safety-net that runs after every auto-memory write, scans the file with a regex marker set (absolute paths, kebab slugs ≥3 parts, `.tausik/tausik` commands, `scripts/*.py` file refs), emits a stderr warning listing up to 5 matches. Warning-only (exit 0) — catches content that bypassed the marker by accident — Аудит после записи с детектом проектных markers
- **Memory marker regex module** (`scripts/hooks/memory_markers.py`) — stdlib-only `detect_markers(text) -> list[Match]` with 4 precision-tuned pattern kinds (`abs_path`, `slug`, `tausik_cmd`, `src_file`); tuned against 14 cross-project preference strings ("user prefers Russian", "likes pytest", "uses VS Code", kebab-case lookalikes) to keep false positives at zero. Shared with upcoming brain-scrubbing pipeline — Отдельный модуль regex для переиспользования
- **Memory Policy rule in context injection** — `build_memory_block()` now begins with a ⚠ warning line explaining the TAUSIK-vs-auto-memory split, visible to the agent on every session start and `/checkpoint`. `session_start.py` Reminders gain a matching bullet so fresh projects (empty DB) still see the rule — Правило политики памяти в инжекте сессии
- **Hook registration** — `bootstrap_generate.py` + `bootstrap_qwen.py` wire both new hooks into PreToolUse / PostToolUse under matcher `Write|Edit|MultiEdit` for Claude Code and Qwen Code alike — Регистрация в bootstrap для обоих IDE

### Changed / Изменено

- **Hook count:** 11 → 13 (added `memory_pretool_block`, `memory_posttool_audit`) — 13 hook-ов в сумме
- **`is_in_claude_memory`** public alias added to `memory_pretool_block.py` so other hooks can import a stable name instead of the underscore-prefixed internal — Стабильный public API между hook-ами

### Fixed / Исправлено

- **Windows stderr encoding** — hook block messages used unicode arrows (`→`) that rendered as literal `→` on cp1251 consoles; replaced with ASCII `->` in user-facing warning text — Windows consoles больше не портят сообщения hook-ов

### Test Coverage / Тесты

- **+78 new tests** — 1105 → 1183 passing. `test_memory_pretool_block_hook.py` (30 cases: block/allow/bypass/tool_result/settings), `test_memory_markers.py` (29 cases: positive × kind, negatives × 14 preferences, dedup, edge, perf budget), `test_memory_posttool_audit_hook.py` (21+ cases: detection, silence on clean writes, non-audited paths, graceful, truncation `...and N more`, binary content, tool_input variants, settings registration)

## [1.2.0] — 2026-04-17

### Claude-Hardening Epic — anti-drift infrastructure

Inspired by [oh-my-claudecode](https://github.com/Yeachan-Heo/oh-my-claudecode) (staged pipelines, Ralph mode, keyword-detector), [prompt-master](https://github.com/nidhinjs/prompt-master) (load-bearing text, Memory Block, 9 dimensions of intent), and the leaked Claude Code architecture analysis on Habr (KAIROS always-on assistant, Dream System memory consolidation). Addresses the real-world problem that agents "drift" — ignore the framework, skip task creation, forget conventions between sessions. 18 tasks shipped across 4 stories (P0/P1/P2/P3).

### Added / Добавлено

- **Load-bearing CLAUDE.md / AGENTS.md / .cursorrules / QWEN.md templates** — generated IDE instructions went from ~30 lines to ~104 lines each, with 13 hard constraints, workflow graph, memory types table, SENAR rules reference, DYNAMIC block. All four IDE files share a single source of truth in `bootstrap/bootstrap_templates.py` (no more drift between IDEs) — Единый источник CLAUDE/AGENTS/cursorrules/QWEN
- **SessionStart hook** (`scripts/hooks/session_start.py`) — auto-injects TAUSIK state (status, active tasks, blocked tasks, Memory Block) into every new Claude Code / Qwen Code session; no manual `/start` needed — SessionStart хук с автоинъекцией состояния
- **UserPromptSubmit hook** (`scripts/hooks/user_prompt_submit.py`) — detects coding-intent keywords in user prompts (EN+RU) and nudges the agent to check for an active task before writing code — Детектор coding-intent с напоминанием
- **Stop hooks** — `scripts/hooks/keyword_detector.py` (drift-announcement detection in agent's last message — blocks stop if "I'll implement" without active task) and `scripts/hooks/session_cleanup_check.py` (warns about open exploration, review-tasks, session timeout) — Два Stop hook'а: keyword detector и session hygiene
- **PostToolUse verify-fix-loop hook** (`scripts/hooks/task_done_verify.py`) — after every successful `task_done`, 5 rule-based heuristics audit the AC evidence (file paths, ✓ markers, test counts, file refs, lint status); 2+ failures trigger a `/review` recommendation — Rule-based Ralph-mode-lite
- **Memory Block re-injection** — new `memory_block()` method + `tausik memory block` CLI + `tausik_memory_block` MCP tool returning compact markdown (recent decisions + conventions + dead ends, ≤50 lines) consumed by `/start`, `/checkpoint`, SessionStart hook — Повторная инъекция проектной памяти для anti-drift
- **`tausik memory compact`** CLI + `tausik_memory_compact` MCP — Dream-System-inspired aggregation of recent `task_logs` into phases / top opening words / top files mentioned — Консолидация логов в паттерны
- **QG-0 9-dimension intent completeness** — `qg0_dimensions_score()` in `service_gates.py` scores every task against {goal, acceptance_criteria, scope, scope_exclude, role, stack, complexity, story_link, evidence_plan}; <5 dims triggers a "CONTEXT" warning (prompt-master principle) — QG-0 расширен до 9 измерений
- **Adversarial critic in `/review`** — new sixth parallel review agent `agents/skills/review/agents/critic.md` hunting for exactly 3 weaknesses the other 5 agents miss (hidden failure modes, silent contract drift, assumption gaps); opt-in "deep mode" runs two critic passes — Adversarial критик в /review
- **`/interview` skill** — Socratic Q&A before complex tasks (max 3 clarifying questions, prompt-master principle) — Сократический Q&A скилл
- **`tausik hud`** CLI — one-screen live dashboard (session + active task + recent logs + gates) inspired by oh-my-claudecode HUD — Live HUD
- **`tausik suggest-model`** CLI + `scripts/model_routing.py` — model recommendation by complexity tier (simple→Haiku 4.5, medium→Sonnet 4.6, complex→Opus 4.7) for manual application via `/fast` — Cost-aware model routing
- **Webhook notifications** (`scripts/notifier.py` + `scripts/hooks/notify_on_done.py`) — Slack / Discord / Telegram webhooks fired on `task_done`; configured via `TAUSIK_SLACK_WEBHOOK` / `TAUSIK_DISCORD_WEBHOOK` / `TAUSIK_TELEGRAM_WEBHOOK` env vars — Webhook-уведомления в 3 канала
- **`CLAUDE_PLUGIN_DATA` env support** — `scripts/plugin_data.py` respects Claude Code's plugin-data convention for skill persistent state; falls back to `.tausik/plugin_data/` — Поддержка CLAUDE_PLUGIN_DATA
- **Mandatory Gotchas section lint** — `tests/test_skills_have_gotchas.py` enforces every SKILL.md has a "## Gotchas" section with real content (Habr recommendation) — Обязательная секция Gotchas
- **No-boilerplate lint** — `tests/test_skills_no_boilerplate.py` blocks re-introduction of "Always respond in user's language" in SKILLs (already covered by CLAUDE.md) — Лин для boilerplate

### Changed / Изменено

- **Bootstrap no longer copies `lib/AGENTS.md`** (which was dogfooding-specific, referenced `scripts/`/`agents/` structure); `generate_agents_md()` now produces a universal AGENTS.md with shared hard constraints — AGENTS.md теперь генерируется, не копируется из lib
- **Skills cleanup** — 12 SKILL.md files had "Always respond in the user's language" boilerplate removed (duplicate of CLAUDE.md Response Language section) — Чистка boilerplate в 12 skill-файлах
- **Shared hook helpers** — `scripts/hooks/_common.py` extracts `tausik_path()`, `has_active_task()`, `is_task_done_invocation()`, `extract_task_done_slug_from_bash()` previously duplicated across 5 hooks (convention #2: Mixin composition) — Рефакторинг общих helper-ов hooks
- **`bootstrap/bootstrap_venv.py`** gets `install_cli_wrapper()` helper (extracted from bootstrap.py to stay under 400-line gate) — CLI wrapper install вынесен
- **Skills count:** 34 → 35 (added `/interview`) — 35 скиллов
- **MCP tools:** 80 → 82 (added `tausik_memory_block`, `tausik_memory_compact`) — 82 MCP инструмента

### Fixed / Исправлено

- **H1 — Bash `"task done"` false-positive** — PostToolUse hooks (`notify_on_done`, `task_done_verify`) used substring match that triggered on `echo "task done today"`, `git log --grep="task done"`, etc. Replaced with a proper regex anchored to the actual `tausik[.cmd] task done <slug>` CLI shape in `_common.py`
- **H2 — `_check_ac_checkmarks` matched too loosely** — `"complete"` substring fired on `incomplete`/`completion`/`completeness`, and the heuristic ran on the full `task show` output (title + goal) rather than notes. Fixed with word-boundary regex `[✓✔]|\b(passed|verified|ok|complete[d]?)\b` plus `_extract_notes_section()`

### Test Coverage / Тесты

- **+177 new tests** — 918 → 1095 passing. Every new module (hooks, templates, routing, aggregates) ships with its own test file.

## [1.1.0] — 2026-04-12

### DX & Adoption Improvements

Inspired by ideas from [Molyanov AI Dev Framework](https://github.com/pavel-molyanov/molyanov-ai-dev) — two-phase planning, TDD enforcement, skill auto-testing. Community request for Qwen Code support ([#1](https://github.com/Kibertum/tausik-core/issues/1)).

### Added / Добавлено

- **Qwen Code (GigaCode) support** — full IDE integration: `.qwen/` directory, `QWEN.md` rules file, MCP config + SENAR hooks in `.qwen/settings.json`, 80 MCP tools + 4 enforcement hooks (task gate, bash firewall, push gate, auto-format) ([#1](https://github.com/Kibertum/tausik-core/issues/1)) — Полная поддержка Qwen Code CLI с хуками
- **TDD enforcement gate** — optional `tdd_order` quality gate verifies test files are modified alongside source code; disabled by default, enable via config — Опциональный gate для TDD-контроля
- **Two-phase planning** — `/plan` now starts with an interview phase (3+ clarifying questions) before decomposition; skip with `--skip-interview` — Двухфазное планирование с интервью
- **Auto-docs update on /ship** — after commit, `/ship` checks for structural changes and suggests updating `references/` documentation — Автообновление документации при /ship
- **`/skill-test` skill** — auto-generates 3-5 test scenarios for any skill and validates them through subagents — Автотестирование скиллов
- **IDE-aware skill catalog** — `skill-catalog.md` now uses correct IDE directory paths instead of hardcoded `.claude/` — Параметризованный каталог скиллов

### Changed / Изменено

- **`--smart` is now default** — stack detection and skill auto-enable run automatically; use `--no-detect` to skip — `--smart` теперь по умолчанию
- **`--init` no longer requires a name** — project name auto-derived from directory; `--init my-name` still works — `--init` без обязательного имени
- `bootstrap.py --ide` now accepts `qwen` and includes it in `all` — Qwen добавлен в выбор IDE
- Supported IDEs: Claude Code, Cursor, **Qwen Code**, Windsurf, Codex — 5 IDE
- Skills count: 33 → 34 (added `/skill-test`) — 34 скилла
- Filesize gate exempts `agents/qwen/mcp/` directory — Исключение для qwen mcp
## [1.1.1] — 2026-04-14

### Fixed

- **MCP tags coercion** — `tausik_dead_end` and `tausik_memory_add` now accept `tags` as both JSON array and string. MCP clients (Claude Code) may serialize array params as JSON strings; added `_coerce_tags()` helper to handle both formats gracefully.

## [1.0.0] — 2026-04-05

### Public Release / Публичный релиз

First public release of TAUSIK. Cross-IDE AI agent framework implementing [SENAR v1.3 Core](https://senar.tech).
Первый публичный релиз TAUSIK. Кросс-IDE фреймворк для AI-агентов, реализующий [SENAR v1.3 Core](https://senar.tech).

### Highlights / Основное

- **Cross-IDE support** — Claude Code, Cursor, Windsurf, Codex with unified skill/role/stack system — Поддержка Claude Code, Cursor, Windsurf, Codex с единой системой скиллов/ролей/стеков
- **31 skills** — from `/start` to `/ship`, covering the full development lifecycle — 31 скилл, покрывающих полный цикл разработки
- **SENAR v1.3 Core compliance (100%)** — Quality gates, metrics, dead ends, explorations, verification checklists — Полное соответствие SENAR v1.3 Core
- **Graph memory** — Project knowledge base with edges, soft-invalidation, FTS5 search — Графовая память проекта с рёбрами, soft-invalidation, FTS5 поиском
- **Autonomous batch mode** — `/run plan.md` executes multi-task plans with subagents — Автономный batch-режим для выполнения планов

### Added / Добавлено

- **Quality Gates** — QG-0 (context gate: goal + AC + negative scenario) and QG-2 (implementation gate: evidence + tests + ac-verified) — Quality gates с жёстким enforcement
- **Claude Code Hooks** — task gate, bash firewall, git push gate, auto-format — Хуки для контроля в реальном времени
- **SENAR Metrics** — Throughput, Lead Time, FPSR, DER, Dead End Rate, Cost per Task — Автоматические метрики
- **Multi-language gates** — pytest, ruff, go-vet, clippy, phpstan, eslint, tsc, and more — Gates для 10+ языков
- **5-agent review pipeline** — quality, implementation, testing, simplification, documentation agents with iterative cycle — 5 параллельных review-агентов с итеративным циклом
- **Dead ends & explorations** — `dead-end` for documenting failures, `explore` for time-bounded research — Документирование тупиков и исследования
- **Graph memory** — Polymorphic edges between memory/decision nodes, 4 relation types, recursive CTE traversal — Полиморфные рёбра, 4 типа связей, обход графа через CTE
- **Structured task logs** — `task_logs` table with phase tracking and FTS5 index — Структурированные логи задач
- **Vendor skills** — `skills.example.json` + `skill activate/deactivate` for third-party extensions — Поддержка сторонних скиллов
- **Bootstrap** — `bootstrap.py --smart --init` for one-command setup with stack detection — Настройка одной командой с детекцией стека
- **Apache 2.0 license** — Open source license — Лицензия Apache 2.0
- **Bilingual docs** — Full documentation in English and Russian — Полная документация на EN и RU
- **CONTRIBUTING.md** — Contributor guide — Гайд для контрибьюторов
- **837 tests** — Comprehensive test suite — Полный набор тестов
