---
slug: brain-docs-en-ru
title: "README + docs/en/shared-brain.md + docs/ru/shared-brain.md"
status: done
epic: shared-brain
story: brain-onboarding-docs
complexity: medium
role: tech-writer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "docs/en/shared-brain.md (новый), docs/ru/shared-brain.md (новый), docs/README.md (edit), README.md (edit), README.ru.md (edit), CHANGELOG.md (edit)"
scope_exclude: "Никакого кода. Не трогать scripts/, tests/, bootstrap/, .claude/. Не обновлять CLAUDE.md dynamic section — это делается через tausik_update_claudemd в /end."
relevant_files:
  - "docs/en/shared-brain.md"
  - "docs/ru/shared-brain.md"
  - "docs/README.md"
  - README.md
  - README.ru.md
  - CHANGELOG.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-04-23T04:39:15Z"
---

## Goal

Секция "Shared Brain" в README. Детальная документация: философия (generalizable only), architecture, setup через wizard, pros/cons, privacy/scrubbing, Outline как альтернатива (линк на TODO). EN + RU версии.

## Acceptance Criteria

1) docs/en/shared-brain.md создан: секции Philosophy (generalizable only, local vs brain split), Architecture (ASCII-диаграмма потока Notion↔SQLite mirror↔MCP), Setup (будущий wizard + ручной setup шаг-за-шагом), Pros/Cons таблица, Privacy (SHA256 hash, scrubbing linter), Edge cases (rate-limit, offline, revoked token). 2) docs/ru/shared-brain.md — полный RU-перевод со всеми секциями (параллель к EN). 3) docs/README.md — добавлена запись "Shared Brain" в таблицы EN и RU. 4) README.md — раздел "## Shared Brain (optional)" (3-5 предложений + линк) после "Memory Discipline (v1.3.0)" перед "What's Inside". 5) README.ru.md — симметричный раздел. 6) CHANGELOG.md — новая секция "## [Unreleased] — Shared Brain pipeline" с 6 задачами (brain-db-schema/local-schema/config-schema/notion-rest-client/pull-sync/search-local), 5 новыми модулями, 102/102 тестами. 7) Negative scenario (errors documented): docs явно описывают 4 failure modes — (a) Notion revoked token → NotionAuthError + fallback на local-only, (b) rate-limit 429 → retry with Retry-After, (c) offline → search_local работает, sync недоступен, (d) Content >180 KB → chunking rules. Каждый из этих error-modes упоминается в Edge Cases секции обоих (EN/RU) docs. 8) Evidence в task_log — «AC verified: N. ... ✓». 9) Проверка file-refs: все ссылки из docs на scripts/*.py ведут на реально существующие файлы.

## Plan

## Rollback

## Journal

- 2026-04-23T04:36:37Z [implementation] — AC verified: 1. docs/en/shared-brain.md создан: Philosophy (generalizable only, local vs brain table-сравнение), Architecture (ASCII-диаграмма Notion↔client↔sync↔mirror↔search↔config), Setup (7 шагов: parent page → 4 databases → integration → access → env var → config → smoke-test с полным Python-кодом), Privacy (4 защиты: SHA256 hash, scrubbing linter, classifier, revocation), Edge cases (7-строчная таблица), Pros/Cons, Alternative Outline TODO ✓ 2. docs/ru/shared-brain.md — полная симметричная RU-версия со всеми секциями ✓ 3. docs/README.md — добавлены записи #14 "Shared Brain" в обе таблицы (EN/RU) с ссылками ✓ 4. README.md — раздел "## Shared Brain (optional, in progress)" после "Memory Discipline (v1.3.0)" перед "What's Inside"; 3-5 предложений с ссылкой на docs/en/shared-brain.md ✓ 5. README.ru.md — симметричный раздел "## Общая память (опционально, в работе)" со ссылкой на docs/ru/shared-brain.md ✓ 6. CHANGELOG.md — новая секция "## [Unreleased] — Shared Brain pipeline" в начале файла перед [1.3.0]; перечислены 6 задач, 5 модулей (brain_schema.py/brain_config.py/brain_notion_client.py/brain_sync.py/brain_search.py), 102/102 тестов, 6 knowledge items (#30-33 decisions + #34 gotcha + #35 convention) ✓ 7. Negative scenarios: Edge cases table покрывает (a) revoked token → NotionAuthError, (b) rate-limit 429 → Retry-After retry, (c) offline → search_local работает, (d) Content >180 KB → chunking — документированы в обоих EN и RU ✓ 8. Все file-refs валидны: ls подтверждает scripts/brain_config.py/brain_schema.py/brain_notion_client.py/brain_sync.py/brain_search.py + references/brain-db-schema.md + docs/en+ru/shared-brain.md существуют. Brain-suite регресс 102/102 зелёный (docs не сломали код) ✓
