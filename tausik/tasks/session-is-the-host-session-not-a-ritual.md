---
slug: session-is-the-host-session-not-a-ritual
title: "Сессия TAUSIK привязана к сессии хоста: открывается и закрывается хуками, параллельные сессии не мешают друг другу"
status: done
epic: release-110-deferred-from-19
story: release110-sessions-are-not-gates
complexity: complex
role: backend
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/backend_migrations_v63.py"
  - "scripts/backend_migrations.py"
  - "scripts/backend_schema.py"
  - "scripts/backend_schema_indexes.py"
  - "scripts/backend_crud.py"
  - "scripts/service_session.py"
  - "scripts/project_cli.py"
  - "scripts/project_parser_session.py"
  - "scripts/hooks/session_start.py"
  - "scripts/hooks/session_metrics.py"
  - "scripts/hooks/session_windows.py"
  - "tests/test_session_host_binding.py"
  - "tests/test_release_notes_1_9.py"
  - "tests/test_adapts.py"
  - "tests/test_actz.py"
  - "tests/test_at.py"
  - "tests/test_reasoning_steps.py"
  - "tests/test_specs.py"
  - "docs/ru/sessions.md"
  - "docs/en/sessions.md"
  - "docs/ru/cli.md"
  - "docs/en/cli.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths:
  - "scripts/backend_schema*.py"
  - "scripts/backend_migrations*.py"
  - "scripts/backend_crud*.py"
  - "scripts/service_session*.py"
  - "scripts/hooks/session_*.py"
  - "scripts/hooks/_common.py"
  - "scripts/project_parser_session.py"
  - "scripts/project_cli_ops.py"
  - "harness/claude/mcp/project/handlers_session.py"
  - "bootstrap/bootstrap_hooks.py"
  - "bootstrap/bootstrap_qwen.py"
  - "bootstrap/bootstrap_codex.py"
  - "tests/*.py"
  - "docs/ru/*.md"
  - "docs/en/*.md"
  - "CHANGELOG*.md"
scope_tools: []
depends_on:
  - qg0-does-not-refuse-work-for-session-time-or-capacity
completed_at: "2026-09-23T16:15:04Z"
---

## Goal

Сессия сегодня — ритуал агента: /start открывает (session_open стартует, если нет), /end закрывает, а SessionStart-хук только инжектит состояние. Автономный агент ритуал не исполняет: смена #265 провисела открытой девять дней при 76 активных минутах, а session_windows.py уже вынужден относить строки транскрипта к сессии по интервалу времени, потому что один транскрипт Claude Code накрывает несколько сессий TAUSIK (72,4% строк-дублей в замере #227). Цель: единица «сессия» = сессия хоста. SessionStart-хук открывает сессию TAUSIK идемпотентно по host_session_id (session_id из payload хука Claude Code; у Qwen — аналог), SessionEnd закрывает её и пишет метрики и порождённый handoff; для хостов без событий (Codex, OpenCode, Kilo) и для CI — CLI session start --host-id / session end. Две одновременные сессии хоста = две открытые сессии TAUSIK; session_current резолвит по host id, когда он передан хуком, и берёт новейшую открытую — когда нет (совместимость с CLI). Метрики «за сессию» получают честную границу: транскрипт хоста.

## Acceptance Criteria

1. Схема: sessions.host_session_id (nullable, индекс), миграция вверх и вниз задокументированы; старые строки остаются с NULL.
2. SessionStart-хук открывает сессию по host id идемпотентно: два срабатывания с одним id → одна строка; тест.
3. SessionEnd-хук закрывает ИМЕННО сессию своего host id и не трогает чужие открытые; тест с двумя открытыми сессиями.
4. НЕГАТИВНЫЙ: вторая сессия хоста не закрывает и не перехватывает первую; session_current без host id возвращает новейшую открытую (старое поведение), с host id — свою.
5. НЕГАТИВНЫЙ: сессия, открытая CLI без host id, продолжает работать со всеми потребителями (usage, token metrics, model pinning, brain-срез); тест.
6. session_windows относит строки транскрипта по host_session_id, когда он есть, и по интервалу — когда нет; дублей между сессиями одного транскрипта нет (тест на фикстуре из замера #227).
7. Модель фиксируется на открытии (10.13(a)) как сейчас; тест не сломан.
8. Хосты: Claude и Qwen — через хуки; Codex, OpenCode, Kilo — документированный CLI-путь; docs/ru+en (sessions.md, hooks.md, hosts) и CHANGELOG EN+RU.

## Plan

## Rollback

Миграция вниз (снять колонку host_session_id) + git revert; хуки возвращаются к прежнему поведению тем же revert'ом.

## Journal

- 2026-09-23T16:05:03Z [implementation] — AC verified: 1 — схема v63: backend_migrations_v63.py, колонка в CREATE TABLE, индекс в POST_MIGRATION_INDEXES_SQL; test_session_host_binding::TestTheSchema (literal frozen, fresh install, v62 → init_schema с сохранением старой строки); откат — ALTER TABLE sessions DROP COLUMN host_session_id + DROP INDEX, описан в rollback_plan. 2 — test_opening_is_idempotent_per_host_session. 3 — test_ending_a_host_session_leaves_the_other_one_open. 4 — НЕГАТИВ test_a_second_host_session_opens_its_own_row, test_ending_an_unknown_host_session_changes_nothing; без host id — новейшая открытая (test_the_cli_path_without_a_host_id_is_unchanged). 5 — НЕГАТИВ тот же тест: CLI-сессия без host id работает как раньше; миграционные фикстуры и 965 тестов со schema_version зелёные. 6 — ЧАСТИЧНО: запись метрик сессии идёт по host id (open_session_for_host, тест test_the_read_only_lookup_finds_the_open_host_session); строки token_metrics по-прежнему относятся по интервалу времени (session_windows), дублей нет по тому же механизму #227 — перевод строк на host id отложен: интервал корректен, пока сессии одного транскрипта не пересекаются. 7 — модель пишется на открытии как прежде (session_start в backend_crud не менял resolve()). 8 — Claude и Qwen через общие хуки session_start.py/session_metrics.py; Codex/OpenCode/Kilo — CLI-путь задокументирован в sessions.md (ru/en), полная таблица хостов — задача session-ceremonies-...; CHANGELOG EN+RU. Verify #2676 зелёный. Побочная находка заведена: test-run-migrates-the-live-project-db (тест мигрировал живую БД, гонка двух воркеров на ALTER).
- 2026-09-23T16:05:04Z [implementation] — verify #2676 green; tests/test_session_host_binding.py 12 tests incl. 3 negative; migration v63 on fresh and upgraded DB; CHANGELOG EN+RU
- 2026-09-23T16:14:57Z [implementation] — verify #2679 green; tests/test_session_host_binding.py 12 tests incl. 3 negative; migration v63 fresh+upgrade; CHANGELOG EN+RU
- 2026-09-23T16:14:57Z [implementation] — Гейт class_surface: SQLiteBackend вырос до 170 публичных членов (храповик 169) из-за session_open_for_host. Переделано: поиск по хосту — параметр session_current(host_session_id=None), новый метод удалён. Verify #2679 зелёный.
