---
slug: spec-uc-is-the-twelfth-spec-type
title: "SPEC-UC — двенадцатый тип спецификации: role human|agent, шаг ссылается на утверждение (RENAR 1.1 §8.5.12, ADR-018)"
status: done
epic: release-110-deferred-from-19
story: release110-renar-11-first-party-and-spec-uc
complexity: medium
role: backend
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/backend_migrations_v64.py"
  - "scripts/backend_migrations.py"
  - "scripts/backend_migrations_postseed.py"
  - "scripts/backend_schema.py"
  - "scripts/backend_schema_specs.py"
  - "scripts/service_specs.py"
  - "scripts/spec_uc.py"
  - "scripts/spec_completeness.py"
  - "harness/claude/mcp/project/tools.py"
  - "tests/test_spec_uc.py"
  - "tests/test_spec_types_closed_list.py"
  - "tests/test_spec_completeness.py"
  - "tests/test_renar_conformance.py"
  - "tests/test_mcp_deployed_layout_resolves.py"
  - "docs/en/mcp.md"
  - "docs/ru/mcp.md"
  - "docs/_generated/constants.json"
  - RENAR-CONFORMANCE.yaml
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths:
  - "scripts/service_specs.py"
  - "scripts/spec_uc.py"
  - "scripts/backend_schema.py"
  - "scripts/backend_schema_specs.py"
  - "scripts/backend_migrations*.py"
  - "scripts/backend_crud_specs.py"
  - "scripts/project_cli_specs.py"
  - "scripts/project_parser_specs.py"
  - "scripts/renar_*.py"
  - "scripts/gate_spec.py"
  - "scripts/spec_completeness.py"
  - "scripts/doc_closed_lists.py"
  - "harness/claude/mcp/project/*.py"
  - "tests/*.py"
  - "docs/ru/*.md"
  - "docs/en/*.md"
  - "docs/_generated/*"
  - "CHANGELOG*.md"
  - RENAR-CONFORMANCE.yaml
scope_tools: []
depends_on:
  - renar-drift-detector-reads-the-site-repo-not-the-standard
completed_at: "2026-09-23T17:12:27Z"
resolution: null
resolution_reason: null
---

## Goal

RENAR 1.1 §8.3 закрывает список типов SPEC на двенадцати: добавлен SPEC-UC (сценарии использования) с полем role: human|agent и ссылкой каждого шага на утверждение SPEC-UI/SPEC-PROC (§8.5.12.1, адрес <id>#n); шаги без ref — нарушение структурной полноты. SPEC_TYPES в service_specs.py несёт 11, детектор дрейфа (после починки пути) это показывает. Цель: тип добавлен в закрытый список и схему (CHECK-ограничение, если есть — миграция), обязательные поля SPEC-UC валидируются при создании, экспорт renar/ несёт тип, детектор молчит.

## Acceptance Criteria

1. SPEC_TYPES = 12, CHECK/валидация БД принимает UC; миграция вверх/вниз задокументирована, если ограничение хранится в схеме.
2. spec add --type UC требует role (human|agent) и хотя бы один шаг с ref в форме адреса; НЕГАТИВНЫЙ: шаг без ref — отказ с текстом §8.5.12.1.
3. Детектор дрейфа на живом корпусе renar-standart: ноль находок по типам (тест на живом корпусе, skip без корпуса).
4. renar export и RENAR-CONFORMANCE.yaml перечисляют 12 типов; тест на число, СЧИТАННОЕ из корпуса (конвенция #673).
5. docs/ru+en spec; CHANGELOG EN+RU.

## Plan

## Rollback

Миграция вниз (снять UC из CHECK) + git revert; существующих SPEC-UC в базе нет.

## Journal

- 2026-09-23T16:30:29Z [implementation] — Область расширена: scripts/backend_schema.py (SCHEMA_VERSION 64 — правка сделана до расширения, признаю), scripts/spec_uc.py (новый модуль проверки тела UC), scripts/doc_closed_lists.py, docs/_generated/*.
- 2026-09-23T16:44:40Z [implementation] — Verify блокировал tests/test_mcp_deployed_layout_resolves.py: обход находил исходное harness/ чужого рабочего дерева .kilo/worktrees/crawling-tangelo (создано владельцем в 15:14, игнорируется git — не трогал). Обход теперь пропускает вложенные checkout'ы (.git внутри) и harness/claude/ на любой глубине; негатив test_a_nested_checkout_is_not_a_deployed_profile.
- 2026-09-23T17:11:42Z [implementation] — AC verified: 1 — SPEC_TYPES = 12, CHECK допускает UC: migration v64 (guarded rebuild, frozen DDL), test_spec_uc::test_an_older_specs_table_is_widened_and_keeps_rows (строки сохранены, повтор — no-op); откат — пересборка обратно, строк UC в БД нет. 2 — НЕГАТИВ test_a_step_without_a_ref_is_refused (текст §8.5.12.1, спецификация не создана), test_a_uc_without_role_or_body_is_refused; позитив test_a_complete_uc_is_accepted. 3 — тест живого корпуса tests/test_renar_standard_drift.py::test_the_live_corpus_agrees_with_us зелёный (ноль находок). 4 — RENAR-CONFORMANCE.yaml перечисляет 12 (manifest-version 24), test_renar_conformance сравнивает с SPEC_TYPES, spec_completeness 12 of 12. 5 — docs mcp.md ru/en, CHANGELOG EN+RU. Verify #2691 зелёный.
- 2026-09-23T17:11:42Z [implementation] — verify #2691 green; tests/test_spec_uc.py incl. 2 negatives; live corpus drift zero; manifest v24
- 2026-09-23T17:12:21Z [implementation] — verify #2691 green; tests/test_spec_uc.py incl. 2 negatives; live corpus drift zero; manifest v24
