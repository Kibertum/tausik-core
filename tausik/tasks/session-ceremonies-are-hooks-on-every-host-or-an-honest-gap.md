---
slug: session-ceremonies-are-hooks-on-every-host-or-an-honest-gap
title: "Церемонии сессии — хуки на каждом хосте, а где событий у хоста нет — честно названный CLI-путь"
status: done
epic: release-110-deferred-from-19
story: release110-sessions-are-not-gates
complexity: medium
role: backend
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "harness/opencode/plugins/tausik-qg0.js"
  - "tests/test_opencode_session_events.py"
  - "tests/test_host_session_table.py"
scope_paths:
  - "harness/opencode/plugins/*.js"
  - "bootstrap/*.py"
  - "tests/*.py"
  - "docs/ru/*.md"
  - "docs/en/*.md"
  - "CHANGELOG*.md"
scope_tools: []
depends_on:
  - session-is-the-host-session-not-a-ritual
completed_at: "2026-09-23T18:34:37Z"
---

## Goal

Замер bootstrap: Claude и Qwen подключают SessionStart, Stop и SessionEnd; Codex — только SessionStart; OpenCode и Kilo — ни одного сессионного события. После привязки сессии к хосту (session-is-the-host-session-not-a-ritual) хосты без событий останутся с ритуалом, и это надо назвать, а не подразумевать. Цель: для каждого хоста из SCAFFOLD_IDES либо хук открытия/закрытия сессии, либо документированный CLI-путь (session start --host-id / session end) с указанием, что именно теряется (порождённый handoff на закрытии, метрики закрытия). Хост проверяется замером бинаря, а не документацией (конвенция #686).

## Acceptance Criteria

1. Таблица хостов (docs ru/en): для каждого хоста SCAFFOLD_IDES — открытие и закрытие сессии, чем обеспечено, версия и дата замера бинаря; тест держит таблицу в согласии с профилями bootstrap (читает профили, а не копирует список).
2. Codex: замер бинаря 0.153.4 (смена #266) — перечень событий хуков содержит SessionStart и SessionEnd; профиль Codex получает оба из общего объявления.
3. OpenCode 1.1.42: плагин слушает session.created → session start --host-id, session.deleted → session end --host-id; тест под Node с фейковой оболочкой.
4. НЕГАТИВНЫЙ: событие без id не открывает ничего; сбой CLI в обработчике событий не бросает исключения в редактор; хост без событий (Kilo, Cursor) не получает мёртвого хука — только документированный CLI-путь.
5. CHANGELOG EN+RU.

## Plan

## Rollback

git revert; профили bootstrap регенерируются.

## Journal

- 2026-09-23T18:33:30Z [implementation] — AC verified: 1. ✓ таблица хостов в docs/en|ru/hooks.md; test_every_host_has_a_row и test_each_claim_matches_the_profile читают профили bootstrap 2. ✓ строка codex: замер бинаря 0.153.4, SessionStart/SessionEnd из общего объявления, проверено test_each_claim_matches_the_profile 3. ✓ плагин OpenCode: session.created/session.deleted -> session start/end --host-id, test_created_and_deleted_open_and_close_the_host_session под Node с фейковой оболочкой 4. ✓ test_an_event_without_an_id_opens_nothing, test_a_failing_cli_never_throws_into_the_editor; Kilo/Cursor в таблице как CLI-путь без хука 5. ✓ CHANGELOG EN+RU. Verify #2721 зелёный.
