---
slug: project-hygiene-sweep-with-ratchets
title: "Гигиеническая уборка проекта с храповиками: мёртвый код по символам, дубликаты, файлы над лимитом, бэкапы БД, проекция задач — и тесты, которые не дают этому отрасти"
status: planning
epic: release-110-deferred-from-19
story: release110-site-docs-and-hygiene
complexity: complex
role: backend
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths:
  - "scripts/*.py"
  - "scripts/hooks/*.py"
  - "harness/claude/mcp/project/*.py"
  - "bootstrap/*.py"
  - ".tausik/config.json"
  - "tests/*.py"
  - "docs/ru/*.md"
  - "docs/en/*.md"
  - "CHANGELOG*.md"
scope_tools: []
depends_on:
  - memory-and-repo-hygiene-sweep-with-a-ratchet
  - repo-inventory-what-is-here-that-should-not-be
completed_at: null
---

## Goal

Замер смены #266: 4468 файлов под git, из них 3139 — проекция задач и памяти в tausik/ (70% дерева; hygiene archive умеет мягко архивировать старые done-задачи, но не применялся); 404 модуля scripts/ и 50 хуков при 520 тестовых файлах; harness/claude/mcp/project/tools.py — 1075 строк при лимите 500 (decision #190); в .tausik лежат бэкапы БД (.bak.v59, .bak.v60, .bak.v61, .bak.pre-redact-263); мёртвые дубликаты и хвосты названы отдельными задачами этой истории (record_direct_edit, throwaway-db-guard, два предиката абсолютности, остаток cli_ops, переименование rag-сервера), memory lint и осиротевшие рёбра — свои задачи. Конвенция #682: мёртвый код ищут ПО СИМВОЛАМ и повторяемо. Цель: одна повторяемая команда уборки (или набор) с замером до/после и храповиками — тестами, которые краснеют при возврате мёртвого символа, росте файла над лимитом без исключения, появлении бэкапа старше срока, росте проекции без архивации.

## Acceptance Criteria

1. Замер ДО в журнале: число мёртвых символов (инструмент назван), файлы над лимитом, размер бэкапов, число файлов проекции, число done-задач старше task_archive.done_age_days.
2. Мёртвые символы удалены или названы намеренно оставленными с причиной; храповик-тест держит список исключений и краснеет на новом мёртвом символе; НЕГАТИВНЫЙ: тест подсаживает мёртвую функцию во временный модуль и требует находку.
3. tools.py либо разрезан до лимита, либо стоит в списке исключений filesize gate с причиной (порождаемый); других файлов над лимитом нет.
4. Бэкапы БД: срок жизни и уборка — механизм (doctor предупреждает, hygiene убирает), рабочее дерево после уборки не несёт бэкапов старше срока.
5. Проекция задач: hygiene archive применён к done-задачам старше срока; ROADMAP и метрики не изменились (тест на числа до/после); НЕГАТИВНЫЙ: архивация не трогает открытые и недавно закрытые задачи.
6. Задачи-части истории (дубликаты, предикаты, cli_ops, rag-rename, orphan edges, schema index drift, memory sweep, repo inventory, ruff/mypy/bandit pins, deliberate gaps) закрыты или их остаток назван в этой задаче с причиной.
7. CHANGELOG EN+RU; docs/ru+en (hygiene, doctor).

## Plan

## Rollback

git revert; архивация задач мягкая (archived_at), обратима командой; бэкапы удаляются только старше срока и после doctor-предупреждения.

## Journal
