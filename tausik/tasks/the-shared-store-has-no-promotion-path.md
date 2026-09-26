---
slug: the-shared-store-has-no-promotion-path
title: "Общая база знаний не принимала записей 26 дней: продвинуть существующую запись нечем"
status: done
epic: release-110-deferred-from-19
story: release110-rag-and-memory-tell-the-truth
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/knowledge_promote.py"
  - "scripts/project_parser.py"
  - "scripts/project_cli_extra.py"
  - "scripts/brain_universality.py"
  - "scripts/service_knowledge.py"
  - "tests/test_knowledge_promote.py"
  - "tests/test_knowledge_write.py"
scope_paths:
  - "scripts/knowledge_promote.py"
  - "scripts/project_parser.py"
  - "scripts/project_cli_extra.py"
  - "scripts/brain_universality.py"
  - "scripts/service_knowledge.py"
  - "tests/*.py"
  - "docs/ru/*.md"
  - "docs/en/*.md"
  - "CHANGELOG*.md"
scope_tools: []
depends_on:
  - the-routing-table-names-two-of-four-stores
completed_at: "2026-09-23T20:09:53Z"
resolution: null
resolution_reason: null
---

## Goal

ЗАМЕР #189: общая база знаний ~/.tausik-knowledge/knowledge.db содержит 2498 решений и 14 памяток. ВСЕ 2498 решений имеют одну и ту же метку времени 2026-08-03T06:04:25Z — это разовый перенос командой `knowledge import-brain`, и 2416 из них пришли из ОДНОГО источника brain:c857d09db23e6822. С тех пор в таблицу решений не добавлено НИ ОДНОЙ записи — 26 дней. Памяток 14, написаны тремя проектами в три даты (03.08 перенос, 05.08 проект ansible, 19.08 проект ypncore).
ЭТОТ ПРОЕКТ НЕ НАПИСАЛ В ОБЩУЮ БАЗУ НИЧЕГО, имея 426 памяток и 270 решений у себя.
ГОРЬКАЯ ДЕТАЛЬ: три из 14 общих памяток — ПРО TAUSIK 1.8 («отвергнутая команда гейта не краснеет, а молча остаётся», «обёртка команды гейта обязана НАЗЫВАТЬСЯ именем инструмента», «verify --task без --relevant-files не сертифицирует закрытие»), и написаны они ПОТРЕБИТЕЛЕМ, а не нами. Знание о фреймворке течёт внутрь от пользователей и не течёт наружу от разработчика.
МЕХАНИЧЕСКАЯ ПРИЧИНА, А НЕ ЛЕНЬ: продвинуть СУЩЕСТВУЮЩУЮ запись в общую базу НЕЧЕМ. Флаг --global есть только у создания (`memory add --global`, `decide --global`); команда `knowledge` умеет export, restore и import-brain. Чтобы поделиться уже записанным знанием, его надо ПЕРЕПЕЧАТАТЬ вручную. Плюс маршрутизатор о третьем адресе молчит (задача the-routing-table-names-two-of-four-stores).
ЧТО ДЕЛАЕТСЯ: `memory promote <id>` и `decide promote <id>` — продвижение существующей записи с сохранением происхождения (origin_project/origin_slug в общей схеме уже есть) и с ОБЯЗАТЕЛЬНЫМ показом того, что именно уедет: общая база НЕ РЕДАКТИРУЕТСЯ, секреты и PII уезжают дословно, и это уже написано в справке --global. Плюс подсказка при записи знания, чей текст не упоминает ничего из этого репозитория.
НЕГАТИВНОЕ: не продвигать автоматически по эвристике. Ровно на этом обжигались решением #221 — классификатор сам решал, что публиковать, и отправил наружу шесть внутренних решений. Продвижение остаётся явным действием человека или агента, но перестаёт требовать перепечатывания.

## Acceptance Criteria

1. tausik knowledge promote --memory ID | --decision ID показывает, что именно уедет в общую базу (тип, заголовок/текст целиком, теги, происхождение) и предупреждает, что общая база не редактируется, а секреты уезжают дословно; без --yes ничего не пишет.
2. С --yes запись копируется в ~/.tausik-knowledge/knowledge.db с origin_project (метка проекта) и origin_slug (стабильный slug локальной записи); локальная запись не меняется и не удаляется.
3. НЕГАТИВНЫЙ: повторное продвижение той же записи отказывает (есть строка с тем же origin_project и origin_slug) — дубликатов нет; несуществующий ID — отказ.
4. НЕГАТИВНЫЙ: автоматического продвижения нет — подсказка об универсальности при записи знания называет команду promote с id записи, но ничего не пишет.
5. docs (cli) en/ru, CHANGELOG EN+RU.

## Plan

## Rollback

Новые подкоманды продвижения поверх существующих схем. Откат — git revert; уже продвинутые записи остаются в общей базе и удаляются вручную.

## Journal

- 2026-09-23T20:07:13Z [implementation] — Сделано: scripts/knowledge_promote.py (preview — весь текст, теги, происхождение, предупреждение о нередактируемой общей базе; promote — копия с origin_project=метка проекта и origin_slug=slug локальной записи, повтор отказывается); tausik knowledge promote --memory|--decision ID [--yes] (без --yes только показ); подсказка универсальности при memory add называет promote с id записи. Отступление: вместо 'memory promote' и 'decide promote' — одна подкоманда в группе knowledge, потому что decide принимает текст позиционно и 'decide promote' читался бы как текст решения.
- 2026-09-23T20:07:14Z [implementation] — AC-1: ✓ tests/test_knowledge_promote.py::test_the_preview_shows_everything_that_leaves_and_the_warning
- 2026-09-23T20:07:14Z [implementation] — AC-1: ✓ tests/test_knowledge_promote.py::test_without_yes_nothing_is_written
- 2026-09-23T20:07:14Z [implementation] — AC-2: ✓ tests/test_knowledge_promote.py::test_promote_copies_with_provenance_and_leaves_the_local_record
- 2026-09-23T20:07:15Z [implementation] — AC-2: ✓ tests/test_knowledge_promote.py::test_a_decision_is_promoted_too
- 2026-09-23T20:07:15Z [implementation] — AC-3: ✓ tests/test_knowledge_promote.py::test_the_same_record_is_not_copied_twice
- 2026-09-23T20:07:16Z [implementation] — AC-3: ✓ tests/test_knowledge_promote.py::test_a_missing_record_is_refused
- 2026-09-23T20:07:16Z [implementation] — AC-4: ✓ tests/test_knowledge_promote.py::test_the_hint_names_the_command_and_writes_nothing
- 2026-09-23T20:07:17Z [implementation] — AC-5: ✓ docs cli en/ru, CHANGELOG EN+RU
