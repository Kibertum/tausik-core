# Changelog

All notable changes to this project will be documented in this file.

This project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased] — SENAR verify redesign + Shared Brain pipeline

### Added — Backlog finish (4 final planning tasks)

Last 4 planning tasks shipped — backlog drained to **388/388 done** (100%):

- **Brain status CLI + skill** ([scripts/brain_status.py](scripts/brain_status.py), [agents/skills/brain/SKILL.md](agents/skills/brain/SKILL.md)) — `tausik brain status [--json]` снапшот состояния brain: enabled, mirror path/size/last-modified, per-category row counts + last_pull_at + last_error from `sync_state`, registered projects (name/canonical/hash), last web_cache write. `collect_status()` graceful: missing mirror / unreadable config / empty registry → consistent dict с `error` field, без crash. Skill SKILL.md документирует. (`brain-skill-status`)
- **Brain move CLI + skill** ([scripts/brain_move.py](scripts/brain_move.py)) — `tausik brain move <id> --to-brain --kind <decision|pattern|gotcha>` или `--to-local --category <decisions|patterns|gotchas>`. Cross-project ownership check (source_project_hash должен совпадать с current project's hash; `--force` override). Web_cache → refused (no local counterpart). На to-local после успеха: archive Notion page (`pages.update(archived=true)`) + delete from mirror, unless `--keep-source`. Story `brain-tausik-integration` + epic `shared-brain` auto-closed. (`brain-skill-move`)
- **Anthropic OSS research** ([references/anthropic-oss-applicability.md](references/anthropic-oss-applicability.md)) — Surveyed 7 наиболее релевантных Anthropic OSS репозиториев (knowledge-work-plugins, anthropic-cli, agent-sdk-workshop, original_performance_takehome, skills, claude-code-action, financial-services-plugins). Identified 9 applicable patterns (5 simple, 3 medium, 1 complex). Top 3 recommended next tasks: `tausik-skill-manifest` (skill.yaml registry), `tausik-metrics-tiers` (bronze/silver/gold/platinum), `tausik-brain-swappable-backend` (decouple from Notion). (`research-anthropic-repos`)
- **markitdown opt-in integration** ([scripts/doc_extract.py](scripts/doc_extract.py), [agents/skills/markitdown/SKILL.md](agents/skills/markitdown/SKILL.md), [references/markitdown-integration.md](references/markitdown-integration.md)) — Discovery: TAUSIK не имел "ручных парсеров документов" — pdf/excel skills делегируют Claude Code `Read` tool. markitdown добавлен как **opt-in** capability (convention #19 zero-deps сохранён): lazy import + graceful `None` если не установлен. CLI `tausik doc extract <file>` + Python API `extract_to_markdown(path)`. Когда использовать: DOCX/PPTX/XLSX/HTML/EPUB. PDF redirect → `/pdf` skill. Future hook: `brain_post_webfetch` мог бы использовать для HTML conversion (noted, not implemented). (`markitdown-integration`)

### Test Coverage — Backlog finish

- **+39 tests** — `test_brain_status.py` (9 tests: disabled, config_load_error, missing_mirror, enabled_empty/with_data, registered_projects, registry_missing, format_status×2), `test_brain_move.py` (19 tests: TestMoveToBrain×10 включая happy paths + scrub_blocked + notion_error + token_missing + brain_disabled + bad_input + not_found + keep_source; TestMoveToLocal×8 включая cross-project ownership × force, web_cache refused, mirror archive), `test_doc_extract.py` (11 tests + 1 skipif integration: is_available, happy path, format_hint, falls_back_to_markdown_attr, missing markitdown/path/empty/exception/unexpected shape).

### Fixed — Review findings MED/LOW (story review-findings-mlow-fix, 11 issues)

Follow-up to the 5 HIGH fixes — 11 MEDIUM/LOW findings from the same multi-agent review:

- **A7 MED** ([scripts/gate_runner.py](scripts/gate_runner.py) `resolve_test_files_for_relevant`) — Resolver теперь использует `os.walk(tests/)` вместо `os.listdir`. Tests в nested dirs (`tests/integration/`, `tests/unit/scoped/`) корректно матчатся вместо silent fallback на full suite. Single-pass index by basename, дедуп между путями. (`review-mlow-resolver-recursive`)
- **B6+B7 MED** ([scripts/brain_schema.py](scripts/brain_schema.py) `_migrate`) — Добавлен `PRAGMA foreign_keys=OFF/ON` envelope (insurance для будущих FK-touching migrations) + `PRAGMA foreign_key_check` после COMMIT (raise on violations). Docstring документирует irreversibility контракт ("failed batch only rolls back current; previously committed migrations stay applied"). (`review-mlow-brain-safety`)
- **B2 MED** ([scripts/brain_project_registry.py](scripts/brain_project_registry.py) `_acquire_lock`) — Docstring документирует "single reclaim per call (reclaimed flag)" контракт + acknowledge небольшой TOCTOU window между `_is_stale_lock` и `os.unlink`. (`review-mlow-brain-safety`)
- **A5 LOW** ([scripts/service_verification.py](scripts/service_verification.py) `run_gates_with_cache`) — `append_notes_fn` теперь типизирован `Callable[[str, str], None] | None` (был `Any`). (`review-mlow-polish-batch`)
- **A6 LOW** ([scripts/project_cli_verify.py](scripts/project_cli_verify.py) `cmd_verify`) — На cache HIT пишется `events` row `action='verify_cache_hit'` для telemetry. Best-effort try/except — никогда не блокирует verify. (`review-mlow-polish-batch`)
- **B4 LOW** ([scripts/brain_init.py](scripts/brain_init.py) `create_brain_databases`) — Per-category try/except. Новый `PartialCreateError(NotionError)` с `created_ids` attribute — partial-create surface'ит реально-созданные ids в orphan-cleanup guidance вместо `<missing>`. (`review-mlow-polish-batch`)
- **B5 LOW** ([scripts/brain_init.py](scripts/brain_init.py) `CliIO.prompt`) — EOF/KeyboardInterrupt branches: `KeyboardInterrupt` → "Aborted by user (Ctrl+C)", `EOFError` → "Aborted: no input available (stdin closed/piped)". Раньше — общее "Aborted by user" вне зависимости от типа. (`review-mlow-polish-batch`)
- **C-L3 LOW** ([tests/test_brain_notion_client.py](tests/test_brain_notion_client.py) `test_token_not_in_retry_log`) — Добавлен `assert len(caplog.records) >= 1` чтобы поймать silent-pass на пустом caplog (дрейф logger config). (`review-mlow-polish-batch`)
- **A2 docstring** ([scripts/service_verification.py](scripts/service_verification.py) `run_gates_with_cache`) — Concurrency note: "WAL safe but duplicate rows accepted; BEGIN IMMEDIATE worse" — accepted limitation. (`review-mlow-polish-batch`)
- **A3 docstring** ([scripts/service_verification.py](scripts/service_verification.py) `compute_files_hash`) — mtime resolution caveat: NTFS 100ns / ext4 1μs / HFS+ 1s / FAT 2s — false cache hits possible на быстрых правках на FAT/HFS+, recommendation для таких FS. (`review-mlow-polish-batch`)

### Test Coverage — Review fixes

- **+8 hardening tests** — `test_gates.py` (+4 TestResolveTestFilesForRelevant: glob_subdirectory_test_files, glob_subdirectory_with_suffix_variants, dedup_when_test_appears_in_multiple_dirs, missing_tests_dir_returns_empty), `test_brain_init.py` (+3 partial create + EOF distinct messages), `test_brain_notion_client.py` (+1 caplog non-empty assertion).

### Fixed — Review findings (story review-findings-fix, 5 HIGH issues)

Multi-agent review caught 5 HIGH-severity findings post-merge of the SENAR verify redesign + hooks widening; addressed in this batch:

- **C1** ([scripts/hooks/memory_pretool_block.py](scripts/hooks/memory_pretool_block.py)) — Memory guard regression: `~/.claude/projects/abc/memory` (directory-form path, no trailing file) больше НЕ блокировался. `os.path.normpath` срезает trailing slash, потом `[:-1]` slice исключает `'memory'` из проверки. Старый guard `rest[1] == 'memory'` это ловил. Fix: `'memory' in segments` без `[:-1]` — basename `memory.md` всё ещё False (segment exact compare), но bare `memory` ловится. (`review-fix-c1-memory-guard-dir`)
- **A9** ([scripts/service_gates.py](scripts/service_gates.py) `_run_quality_gates`) — Tier mapping регрессия: scope hardcoded в `'lightweight'` для ВСЕХ задач. Нарушал SENAR Rule 5 — auditor querying `verification_runs WHERE scope='critical'` получал 0 строк. Fix: scope резолвится через `_determine_checklist_tier(task)` (simple→lightweight, medium→standard, complex→high), `is_security_sensitive(relevant_files)` override → `'critical'`. (`review-fix-a9-tier-mapping`)
- **A4** ([scripts/service_verification.py](scripts/service_verification.py)) — Security bypass дыры: `auth.py`/`payment.py`/`billing.py` в корне НЕ матчатся (требовало `/auth/` со слэшами). Также не покрыты oauth/sso/saml/crypto/secrets/keys/admin/rbac/webhook/jwt/session/2fa/mfa/signup/login/password. `.env`/`.pem`/`.key`/`.p12`/`.pfx`/`.crt`/`.asc`/`.gpg` extensions тоже игнорировались. Fix: `_SECURITY_PATH_TOKENS` расширен +16 tokens; новые `_SECURITY_BASENAMES` frozenset для root-level `*.py/.ts/.go`; новый `_SECURITY_EXTENSIONS` frozenset; `is_security_sensitive` объединяет 3 проверки. (`review-fix-a4-security-bypass-tokens`)
- **A1** ([scripts/service_verification.py](scripts/service_verification.py), [scripts/project_cli_verify.py](scripts/project_cli_verify.py)) — Cache key не включал резолвенный gate command. Изменение `project_config.DEFAULT_GATES['pytest']['command']` оставляло старые зелёные runs валидными → стейл-кэш с НОВОЙ командой. Fix: новый `resolve_gate_signature(trigger)` — sha256 over sorted gate name+command+severity tuples, 16-char hex; `cache_command` теперь `f'trigger=task-done|sig={sig}|files=...'`. На load_config failure → fallback `'unavailable'` (не блокирует verification). (`review-fix-a1-cache-key-includes-cmd`)
- **H2** ([tests/test_service_verification.py](tests/test_service_verification.py)) — Integration test gap: `run_gates_with_cache` (главный orchestrator) тестировался только через примитивы. Регрессия в `cache_command` formatting прошла бы незаметно. Fix: новая `TestRunGatesWithCacheIntegration` с 6 end-to-end сценариями (miss-then-hit, security bypass, mtime invalidation, red run, append_notes на hit/miss). (`review-fix-h2-cache-integration-test`)

### Added — SENAR verify redesign (epic senar-verify-redesign)

- **Scoped per-task pytest gate** ([scripts/gate_runner.py](scripts/gate_runner.py), [scripts/project_config.py](scripts/project_config.py)) — новый `{test_files_for_files}` substitution + `resolve_test_files_for_relevant(relevant_files)` (basename heuristic + glob `tests/test_<stem>_*.py` варианты + test-file passthrough). Default pytest gate command изменён на `pytest -x -q {test_files_for_files}`. Без `relevant_files` substitution выдаёт `tests/` — fallback на полный suite (regression-safe). Раньше: full pytest на каждом `task done` (~3 мин), что нарушало SENAR Rule 5 tiering и делало Rule 9.5 audit redundant. Теперь: scoped по relevant_files задачи (`senar-verify-tiered`, Phase 1) — Pytest gate теперь scoped, не full suite
- **Verification cache (verification_runs table + lookup)** ([scripts/service_verification.py](scripts/service_verification.py), schema v16) — `compute_files_hash` (SHA256 over canonical path + mtime_ns + size, sorted), `record_run`, `lookup_recent_for_task` (misses on red/files_hash mismatch/command mismatch/stale ≥10 мин), `is_security_sensitive` (hooks/, /auth/, /payment/, /payments/, /billing/ → cache disabled). `service_gates._run_quality_gates` теперь делает lookup до запуска gates — cache hit пропускает их + лог в notes "Gates: cache hit (verify run #X)". Security-sensitive файлы всегда re-verify, не доверяем cache (`senar-verify-tiered`, Phase 2) — Cache reuse: повторный task done на тех же файлах в окне 10 мин — мгновенно
- **`tausik verify` CLI** ([scripts/project_parser.py](scripts/project_parser.py), [scripts/project_cli_extra.py](scripts/project_cli_extra.py)) — `tausik verify [--task slug] [--scope {lightweight,standard,high,critical,manual}]` запускает gates scoped к relevant_files задачи (или unscoped) и записывает результат в `verification_runs`. Полезно для ad-hoc проверки в середине работы (`senar-verify-tiered`, Phase 2) — Ad-hoc verify CLI с записью в кэш
- **CLAUDE.md QG-2/Rule 5 переписаны** — раздел "QG-2 Implementation Gate" (`Ограничения`) явно описывает scoped pytest + cache window + security bypass; раздел "Rule 5 Verification Checklist" в SENAR Compliance таблице обновлён с упоминанием scope-by-relevant_files; Архитектура секция добавляет `service_verification.py` к Gates слою (`senar-verify-tiered`, Phase 3) — Документация QG-2 отражает новый scoped + cache flow

### Test Coverage — SENAR verify

- **+30 unit tests** в `test_service_verification.py` — `compute_files_hash` (empty, none, mtime change, order-independent, missing sentinel, file appearance, skip non-string), `is_security_sensitive` (5 positive paths, 4 negative, empty/none, any-match), `record_run` + `lookup_recent_for_task` (hit, no-runs, files_hash mismatch, command mismatch, red run, stale, takes most recent, empty slug), `is_cache_allowed` (safe/security/empty)
- **+13 unit tests** в `test_gates.py` — `TestResolveTestFilesForRelevant` (empty, basename match, glob suffixes, no match, test-file passthrough, dedup, nonexistent paths, non-string entries, Windows backslash) + `TestPytestGateScopeSubstitution` (substitution uses mapped tests, falls back to full suite, default uses new substitution token)

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

### Fixed / Исправлено — Storage hardening batch

Пакет из 6 MED-исправлений в `brain_sync` + `brain_config` + `brain_runtime`, найденных при review2:

- **WAL mode** ([scripts/brain_sync.py](scripts/brain_sync.py) `open_brain_db`) — `PRAGMA journal_mode=WAL` сразу после connect, перед `apply_schema`. Устраняет SQLITE_BUSY между concurrent sync'ом и MCP read'ом на одном mirror'е. WAL — best-effort: `:memory:` / read-only FS / сетевые диски silently откатываются к default rollback journal, не raise (`brain-schema-wal-mode`) — WAL для параллельного чтения и записи
- **ISO timestamp compare** ([scripts/brain_sync.py](scripts/brain_sync.py) `sync_category`) — max_edited вычисляется через `_iso_epoch` (parsed UTC seconds), не лексикографически. Исправлен баг: `"...10:00:00Z"` > `"...10:00:00.000Z"` в ASCII-сравнении, но это ТОТ ЖЕ момент. Без фикса cursor мог регрессировать, если в батче смешаны форматы. Использует `brain_hook_utils.parse_iso_to_epoch` (shared с brain-search-proactive) (`brain-sync-iso-timestamp-compare`) — Корректный temporal compare смешанных ISO-форматов
- **Single-transaction atomicity** ([scripts/brain_sync.py](scripts/brain_sync.py) `sync_category`) — success path: один `conn.commit()` после всех upsert'ов и cursor-update'а. Error path: `conn.rollback()` снимает partial upsert'ы, затем отдельная best-effort tx пишет `last_error` в `sync_state`. Раньше было 2 commit'а в except-ветке — partial state при падении между ними (`brain-sync-transaction-atomicity`) — Атомарная single-tx sync-операция
- **Strict `after` cursor filter** ([scripts/brain_sync.py](scripts/brain_sync.py) `_make_filter`) — `{"last_edited_time": {"after": cursor}}` вместо `on_or_after`. Boundary-страница (edited == cursor) больше не re-fetches на каждом sync'е (`brain-sync-cursor-advance`) — Исключение boundary re-fetch
- **NFC normalization** ([scripts/brain_config.py](scripts/brain_config.py) `compute_project_hash`) — `unicodedata.normalize("NFC", name)` перед canonicalize/hash. Фикс: precomposed é (U+00E9) и decomposed e+U+0301 давали разные project_hash → двойная регистрация одного проекта (`brain-config-unicode-nfc`) — Единый hash для NFC и NFD имён
- **Mirror-path contract** ([scripts/brain_runtime.py](scripts/brain_runtime.py) `try_brain_write_*`) — оба wrapper'а теперь зовут `get_brain_mirror_path()` без аргумента. Раньше передавали уже-merged brain dict → `load_brain(merged).get("brain", {})` = `{}` → user's `local_mirror_path` silently отбрасывался, использовался DEFAULT. Regression-тесты с patched `load_config` + captured `open_brain_db` arg (`brain-config-mirror-path-contract`) — Пользовательский mirror path больше не теряется

### Changed / Изменено

- **brain_sync split** — Notion property readers + per-category mappers (`_concat_text`, `_read_prop`, `_prop_*`, `map_decision` / `map_web_cache` / `map_pattern` / `map_gotcha` + `MAPPERS_BY_CATEGORY`) вынесены в новый [scripts/brain_notion_props.py](scripts/brain_notion_props.py) (~142 lines). `brain_sync.py` сократился до 328 lines — под 400-line filesize gate. `map_page_to_row` остался в brain_sync как dispatcher — Выделение Notion parsers в отдельный модуль

### Fixed / Исправлено — review3 pass

4 findings from the third defensive review pass on commits af0a156 / 4a24c1a / 2e56a64:

- **[M1] `get_brain_mirror_path` shape detection** ([scripts/brain_config.py](scripts/brain_config.py)) — функция теперь принимает три формы: `None` (consults load_config), top-level `{"brain": {...}}`, и already-merged brain dict `{"enabled": ..., "local_mirror_path": ...}`. Детектит merged по отсутствию ключа `"brain"` + наличию любого из merged-shape маркеров (`enabled` / `local_mirror_path` / `database_ids`). Устраняет footgun: предыдущий фикс в `brain_runtime.try_brain_write_*` обходил баг через `get_brain_mirror_path()` без аргумента, но сама функция оставалась миной для будущих callers. Regression-тесты для обеих shapes — Контракт функции поддерживает обе shape
- **[M1 docs] docs/en|ru/shared-brain.md** — smoke-test snippet упрощён: `load_brain()` + `validate_brain()` + `get_brain_mirror_path()` все без аргументов, плюс параграф про три поддерживаемые формы входа — Документация смоук-теста без ambiguous cfg
- **[M2] Hoisted import** ([scripts/brain_sync.py](scripts/brain_sync.py)) — `from brain_hook_utils import parse_iso_to_epoch` на module scope. Раньше импорт был внутри `_iso_epoch` (вызывается per-page в sync loop) — per-call attribute lookup на холодном sync'е тысяч страниц — Импорт вынесен из hot loop
- **[L1] auto-BEGIN invariant comment** ([scripts/brain_sync.py](scripts/brain_sync.py) `sync_category`) — inline-комментарий фиксирует инвариант: `conn.rollback()` в except-ветке полагается на implicit BEGIN от первого `upsert_page`. Если рефакторинг добавит DML раньше в `_get_sync_state`, rollback boundary изменится — Комментарий защищает rollback-инвариант
- **[L2] Dead test удалён** ([tests/test_brain_storage_hardening.py](tests/test_brain_storage_hardening.py)) — `test_memory_db_falls_back_silently` не вызывал `open_brain_db`, тестировал поведение sqlite3 напрямую. `test_wal_failure_does_not_raise` покрывает настоящий контракт — Лишний тест сняли

### Added — MCP write/read hardening batch

- **Token-missing warning in MCP read handlers** ([agents/{claude,cursor}/mcp/brain/handlers.py](agents/claude/mcp/brain/handlers.py)) — `handle_brain_search` и `handle_brain_get` теперь явно сигналят пользователю когда `cfg.enabled=true` но `client=None` (token env unset): инжектят warning с именем env-переменной из `cfg.notion_integration_token_env` в первый слот `result.warnings`. Раньше handler молча пропускал Notion fallback — пользователь не отличал offline от no-token. Generic fallback текст когда `notion_integration_token_env` отсутствует/пуст. Disabled brain не получает warning (status quo) (`brain-mcp-token-missing-warning`) — Явный warning о ненастроенном токене вместо тихого пропуска

### Fixed — MCP write/read hardening batch

- **Dead category-fallback removed** ([scripts/brain_mcp_write.py](scripts/brain_mcp_write.py) `format_store_result`) — `cat = result.get("error_category") or result.get("category") or "unknown"` упрощено до `result.get("error_category") or "unknown"`. `store_record` пишет только `error_category` — мёртвая ветка скрывала бы будущие typos (`brain-mcp-write-dead-code-cleanup`) — Убрана defensive ветка, скрывавшая typos

### Changed — Hooks widening batch

- **Memory-block guard расширен на .claude/\*\*/memory/** ([scripts/hooks/memory_pretool_block.py](scripts/hooks/memory_pretool_block.py)) — `_is_in_claude_memory` теперь матчит любой `memory` сегмент под `~/.claude/`, а не только `projects/<slug>/memory/`. Silently-unguarded paths (`~/.claude/memory/`, `~/.claude/agents/<name>/memory/`, `~/.claude/plugins/.../memory/`) теперь блокируются. `memory_posttool_audit` расширяется автоматически (импортирует `is_in_claude_memory`). BLOCKED stderr обновлён. Файл с именем `memory.md` (не под директорией `memory/`) не блокируется. Substring `somememory/` / `memoryold/` тоже не ложноблокируются (`hooks-pretool-block-path-patterns`) — Гвард памяти теперь ловит все поддиректории memory под .claude/
- **Slug regex расширен с {2,} до {1,}** ([scripts/hooks/memory_markers.py](scripts/hooks/memory_markers.py)) — `_SLUG_RE` ловит 2-сегментные slug'и (`my-app`, `brain-init`, `hystolab-ru`), но `detect_markers` применяет precision guard: 2-seg slug попадает в результат только при корреляции с higher-precision детектором (`abs_path` / `src_file` / `tausik_cmd`) или 3+ seg slug'ом в том же тексте. Standalone 2-seg slug → empty (консервативно, английские kebab-compounds типа `kebab-case` / `ts-node` / `switch-case` / `double-quoted` / `single-quoted` не флагуются) (`hooks-markers-slug-regex-widen`) — Ловим короткие project slug'и при корреляции, не шумим на English kebab

### Added — Misc hardening batch (Batch 4)

- **Qwen Code brain MCP registration** ([bootstrap/bootstrap_qwen.py](bootstrap/bootstrap_qwen.py)) — `generate_settings_qwen` теперь регистрирует `tausik-brain` MCP server параллельно `tausik-project`/`codebase-rag` (тот же pattern что в `bootstrap_generate.py:241-246`). Раньше Qwen users молча оставались без brain. Silent skip когда `target_dir/mcp/brain/server.py` отсутствует — не ломает чистые qwen-only проекты (`bootstrap-qwen-brain-mcp`) — Qwen users теперь получают brain MCP при bootstrap
- **Brain schema migration path** ([scripts/brain_schema.py](scripts/brain_schema.py)) — `apply_schema` теперь читает `brain_meta.schema_version` после CREATE TABLE; если db_version > SCHEMA_VERSION → `RuntimeError("Brain DB schema vN newer than code v1; update tausik-lib")` (newer-code guard); если db_version < SCHEMA_VERSION → запускает новый `_migrate(conn, from_version)` helper. `BRAIN_MIGRATIONS = {}` placeholder dict с docstring контракта (sorted-by-key, single-tx, irreversible, bump после успешного COMMIT). Раньше `SCHEMA_VERSION=1` записывался но никогда не читался — нет ALTER strategy для будущих v2/v3 (`brain-schema-migration-path`) — Foundation для будущих brain schema bump'ов

### Added — Init/registry hardening batch

- **Orphan database cleanup guidance** ([scripts/brain_init.py](scripts/brain_init.py) `run_wizard`) — пост-create секция (register_project + all_project_names + config_ops.save) обёрнута в try/except. На любую ошибку после успешного `create_brain_databases` новый helper `_print_orphan_cleanup_guidance` печатает все 4 `category: db_id (title)` с инструкцией Archive via Notion UI, затем raise `WizardError("Post-create step failed ...")`. Раньше пользователь получал orphan Notion databases и не знал какие именно архивировать. Покрытие: registry RegistryLockError, config_ops.save OSError, happy path не регрессирует (`brain-init-orphan-cleanup`) — Видимая cleanup-инструкция вместо тихих orphan-ов
- **CliIO EOF/KeyboardInterrupt → WizardError** ([scripts/brain_init.py](scripts/brain_init.py)) — default `CliIO` поднята на module-level (раньше локальный `_CliIO` в `cmd_brain`); `prompt()` оборачивает `input()` в `try/except (EOFError, KeyboardInterrupt)` → raise `WizardError("Aborted by user.")` вместо raw traceback. project_cli_ops.cmd_brain использует `brain_init.CliIO`. Покрывает: piped stdin (EOFError) и Ctrl+C (KeyboardInterrupt) во время interactive wizard prompt'ов (`brain-init-input-error-handling`) — Чистый abort вместо traceback при piped stdin / Ctrl+C
- **Stale-lock recovery** ([scripts/brain_project_registry.py](scripts/brain_project_registry.py) `_acquire_lock`) — SIGKILL'нутый wizard оставлял `.lock` файл навсегда: новые `init`/`register_project` зависали до timeout. Новые `_pid_alive(pid)` (OS-агностичный через `os.kill(pid,0)`, корректно обрабатывает ProcessLookupError/PermissionError/Windows ERROR_INVALID_PARAMETER) + `_is_stale_lock(lock_path)` (stale если pid мёртв ИЛИ mtime > `_STALE_LOCK_AGE_S=30s`). На FileExistsError проверяем stale → unlink + log warning + retry (ровно 1 раз через `reclaimed` flag). Регрессия: live + fresh lock всё ещё блокирует. Boundary cases: malformed lock content fall-back на mtime, read OSError → not stale (conservative) (`brain-registry-stale-lock-recovery`) — Wizard recovery от orphan locks без manual cleanup

### Test Coverage / Тесты

- **+102 new tests** — `test_brain_schema.py` (17), `test_brain_config.py` (20), `test_brain_notion_client.py` (26), `test_brain_sync.py` (15), `test_brain_search.py` (24). Entire brain-suite green in 2 s; no network I/O (client tests inject `_Recorder`/`_ClockSleep`). Pre-existing 918 tests unaffected.
- **+19 hardening tests** — `test_brain_mcp_handlers.py` (+6 token-missing warning + boundary), `test_brain_mcp_write.py` (+3 NotionAuthError/RateLimitError(retry_after=42)/RateLimitError(retry_after=None default) + 2 ok_not_mirrored on upsert/map_page_to_row failure + 1 typo `category` → unknown), `test_brain_notion_client.py` (+7 secret-leak defense: `_LEAK_TOKEN` not in `repr(client)`, `NotionAuthError`/`NotionNotFoundError`/`NotionRateLimitError`/`NotionServerError`/`NotionNetworkError` strings + `caplog` retry log) (`brain-mcp-write-error-class-tests`, `brain-mcp-write-ok-not-mirrored-test`, `brain-notion-client-secret-leak-test`)
- **+9 hooks widening tests** — `test_memory_pretool_block_hook.py` (+3 new block paths: bare_claude_memory, agents_memory, deeply_nested_memory + 3 negatives: memory.md file, somememory/, memoryold/), `test_memory_markers.py` (+6 TestTwoSegmentSlugs: standalone 2-seg dropped, corroborated with abs_path/src_file/tausik_cmd/3seg-slug kept, 3-seg alone regression) (`hooks-pretool-block-path-patterns`, `hooks-markers-slug-regex-widen`)
- **+10 init/registry tests** — `test_brain_init.py` (+3: registry_failure_prints_orphan_guidance, config_save_failure_prints_orphan_guidance, happy_path_prints_no_orphan_guidance), `test_brain_project_registry.py` (+7: dead_pid_reclaimed, expired_mtime_reclaimed, live_fresh_not_reclaimed regression, malformed_reclaimed_after_ttl, malformed_fresh_blocks boundary, is_stale_lock_missing_returns_false, pid_alive_rejects_nonpositive) (`brain-init-orphan-cleanup`, `brain-registry-stale-lock-recovery`)
- **+3 CliIO tests** — `test_brain_init.py` (TestCliIOPrompt: returns_input_normally, eof_raises_wizard_error, keyboard_interrupt_raises_wizard_error) (`brain-init-input-error-handling`)
- **+3 qwen MCP tests** — `test_bootstrap_qwen.py` (qwen_registers_brain_when_server_present, qwen_skips_brain_when_server_missing, qwen_preserves_user_added_servers) (`bootstrap-qwen-brain-mcp`)
- **+5 brain schema migration tests** — `test_brain_schema.py` (BRAIN_MIGRATIONS dict exists, apply_schema idempotent when migrations empty, raises_when_db_newer guard, migrate_applies_pending_versions, migrate_skips_already_applied, migrate_rolls_back_on_failure) (`brain-schema-migration-path`)

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
