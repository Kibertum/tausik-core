---
slug: schema-migrations-of-the-release-run-as-one-campaign
title: "Десять миграций схемы в одном релизе, написанных независимо, — отдельный риск, а не сумма задач"
status: done
epic: release-111-economy-draft
story: release111-release-proof
complexity: medium
role: architect
stack: python
tier: moderate
call_budget: 45
defect_of: null
scope: "Only schema changes actually proposed by 1.11; migration order; backup/restore; state roundtrip"
scope_exclude: null
relevant_files:
  - "scripts/backend_schema.py"
  - "scripts/backend_migrations*.py"
  - "tests/test_release111_upgrade.py"
  - "docs/en/upgrade.md"
  - "docs/ru/upgrade.md"
scope_paths:
  - "scripts/backend_schema.py"
  - "scripts/backend_migrations*.py"
  - "tests/test_release111_upgrade.py"
  - "docs/en/upgrade.md"
  - "docs/ru/upgrade.md"
  - "tausik/"
  - "changelog.d/"
  - ".tausik/planning/release-111/"
scope_tools: []
depends_on:
  - "1-11-establish-a-codex-usage-baseline-that-can"
  - r111-compound-workflow-results
  - r111-glm-host-usage-adapter
  - r111-runtime-observation-contract
completed_at: "2026-10-01T18:19:51Z"
resolution: obsolete
resolution_reason: "Stale premise: 1.11 has zero portable TAUSIK schema deltas (v67→v67). No migration number, upgrade campaign, reverse migration or new schema test is applicable; adding them would create ceremony without behavior."
tracker_refs:
  - "github#156"
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

РИСК, ОЦЕНЁННЫЙ ЗАМЕРОМ В #189, А НЕ ПРЕДЧУВСТВИЕМ. Из 77 задач релиза 19 упоминают схему или миграцию. Из них НОВЫЕ СУЩНОСТИ вводят как минимум шесть: TC как артефакт, ACTZ, AT, граф артефактов с рёбрами и происхождением, красная история теста, жизненный цикл решений. Плюс изменения существующих: session_id становится необязательным (47->48), два новых типа SPEC, изъятие состояния client-ready из машины состояний ADAPT с миграцией уже подписанных, идентичность деятеля в квитанции.
ПОЧЕМУ ЭТО ОТДЕЛЬНЫЙ РИСК, А НЕ СУММА ЗАДАЧ: SCHEMA_VERSION за релиз уедет примерно с 47 на 55+; каждая миграция обязана иметь обратную; производное дерево tausik/ меняет состав при каждой новой сущности, а гейт state_roundtrip сверяет его целиком. Десять независимо написанных миграций в одном релизе — это десять шансов на невозвратный апгрейд у потребителя, который узнает о нём при обновлении сабмодуля.
ЧТО ДЕЛАЕТСЯ: миграции релиза ведутся ОДНОЙ КАМПАНИЕЙ с общими правилами, а не каждая по вкусу автора. Правила, обязательные к соблюдению каждой задачей, вводящей сущность: (1) обратная миграция существует и проверена; (2) экспорт и импорт новой сущности покрыты roundtrip-тестом до её использования; (3) порядок номеров версий закреплён заранее, чтобы две параллельные задачи не заняли один номер — при многоагентной работе это произойдёт обязательно; (4) заметки к релизу перечисляют переход версий схемы одной строкой.
НЕГАТИВНОЕ: кампания не имеет права стать очередью, через которую всё проходит по одному — это убьёт параллель. Предмет — общие ПРАВИЛА и резервирование номеров, а не последовательное исполнение.
ПЕРВЫЙ ШАГ — НЕ КОД: перечислить поимённо все задачи релиза, вводящие или меняющие схему, и закрепить за ними номера версий.

## Acceptance Criteria

AC-1 Inventory actual 1.11 schema changes before allocation; do not assume the old 47-to-55 forecast is current or force deferred memory/TC migrations into 1.11. AC-2 Reserve non-conflicting migration order and verify upgrade from supported 1.10 state plus repeated bootstrap; previous telemetry remains explicitly compatible/legacy. AC-3 Each new persisted portable entity has export/import roundtrip where applicable; local usage data remains local by policy. AC-4 Negative: interrupted/failed upgrade preserves or restores the original database, never silently marks missing usage zero; backward path is a tested reverse migration or documented tested backup restoration. AC-5 The release names exact old/new schema versions and publishes one coherent upgrade/rollback procedure.

## Plan

[{"step": "Inventory 1.11 schema deltas with the observation-contract design before code changes.", "done": false}, {"step": "Reserve migration order and implement/verify backup, upgrade and reverse/restore behavior.", "done": false}, {"step": "Check supported 1.10 upgrades, repeated runs and export/import boundaries; record actual version span.", "done": false}]

## Rollback

Revert only this task's changes; preserve pre-change behavior and historical evidence. For migrations verify database backup restoration.

## Journal

- 2026-10-01T15:22:08Z [planning] — Execution ordering corrected: final upgrade campaign must follow actual persisted usage/workflow designs, not precede them. Observation contract requires no schema migration; current source is schema 67, so legacy 47-to-55 forecast is not applicable. Added baseline/GLM/workflow predecessors to prevent premature release proof.
- 2026-10-01T18:19:50Z [planning] — Inventory evidence: current and HEAD SCHEMA_VERSION are both 67; no diff exists in backend_schema, backend_migrations*, backend_init, knowledge_db, migration/schema/upgrade tests. 1.11 usage/routing/context changes use read-only native sources, local sidecars or existing meta. Existing v62→67 upgrade/backup protections remain unchanged.
