---
slug: renar-first-party-confirmation-is-available
title: "Подтверждение первой стороной (RENAR 1.1 §1.4.4): выход из «несоответствие по декларации» — при замороженном концепте и подписи ответственного лица"
status: planning
epic: release-110-deferred-from-19
story: deferred-110-outward-loop-and-test-authorship
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
  - "scripts/renar_*.py"
  - "scripts/service_actz.py"
  - "scripts/service_adapts.py"
  - "scripts/gate_at_freshness.py"
  - "scripts/gate_qg0_renar.py"
  - "scripts/backend_schema*.py"
  - "scripts/backend_migrations*.py"
  - "scripts/backend_crud*.py"
  - "scripts/project_cli_*.py"
  - "scripts/project_parser*.py"
  - "harness/claude/mcp/project/*.py"
  - "tests/*.py"
  - "docs/ru/*.md"
  - "docs/en/*.md"
  - "CHANGELOG*.md"
scope_tools: []
depends_on:
  - renar-drift-detector-reads-the-site-repo-not-the-standard
completed_at: null
resolution: null
resolution_reason: null
tracker_refs:
  - "github#186"
started_model_id: null
started_model_version: null
done_model_id: null
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
---

## Goal

TAUSIK объявляет RENAR non-conformant по §1.5.4: внутренний продукт без независимого представителя клиента, двусторонняя подпись ACTZ невозможна (решение #292). RENAR 1.1 вводит §1.4.4 — вид применимости «подтверждение первой стороной»: вход — ЗАМОРОЖЕННЫЙ ПИСЬМЕННЫЙ КОНЦЕПТ (V6: автор + отметка времени), занимающий место ТЗ; ACTZ и релизный гейт AT беспредметны; состязательный обзор обязателен без исключений (AR с моделью рецензента, ACR ведётся); манифест confirmation: first-party; готовность предъявляется записью верификации версии комплекта с подписью ответственного лица. Совмещение ролей — норма. Это единственный путь TAUSIK к заявлению RENAR-N, и он требует от владельца концепта и подписи — решение владельца, не агента. Цель задачи: механизм готов и ждёт концепта; без концепта манифест остаётся non-conformant §1.5.4 (без изменений).

## Acceptance Criteria

1. Сущность «концепт» (или SPEC/док с ролью источника) с полями автор/время/подпись V6 и командой заморозки; source.tz-section ADAPT может указывать на раздел концепта.
2. renar conformance: при наличии подписанного концепта SCOPE_EXCLUSION снимается, манифест несёт confirmation: first-party и вид §1.4.4; НЕГАТИВНЫЙ: без подписанного концепта — прежняя декларация §1.5.4 слово в слово (тест на текст).
3. Гейты ACTZ (actz-integrity, decided-in) и AT (gate_at_freshness, релизная готовность) под first-party переходят в явное состояние «беспредметны по §1.4.4» — в выводе и YAML, не тишина (НЕГАТИВНЫЙ: попытка подписать ACTZ одним лицом за обе стороны — отказ с §5.5.3).
4. Состязательный обзор: AR с моделью рецензента обязателен для каждого ADAPT; вердикт «находок нет» требует обоснования (§1.4.4 п. 3); ACR печатается в metrics.
5. Записан вопрос владельцу в задаче: готов ли он заморозить концепт TAUSIK и подписать; до ответа задача не стартует (блокер названа).
6. docs/ru+en renar; CHANGELOG EN+RU.

## Plan

## Rollback

git revert; манифест регенерируется в прежнее состояние; данные концепта остаются в БД как обычная запись.

## Journal
