---
slug: kontrakt-agenta-suschestvuet-tolko-po-russki-a
title: "Контракт агента существует только по-русски, а CLAUDE.md называет его полным"
status: planning
epic: release-110-deferred-from-19
story: release110-site-docs-and-hygiene
complexity: complex
role: null
stack: null
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: null
resolution: null
resolution_reason: null
---

## Goal

Агент, читающий английскую ветку документации, имеет полный контракт. Сейчас docs/ru/agent-contract.md — 527 строк, на которые CLAUDE.md ссылается как на полный контракт агента, — существует только по-русски, и i18n-strategy при этом утверждает, что вся документация локализована полностью.

## Acceptance Criteria

1. Замер ДО: 527 строк только ru; на документ ссылаются CLAUDE.md, docs/ru/hooks-events.md (раздел остаточной границы) и страница намеренных пробелов. 2. Английская половина существует и структурно совпадает: audit_translation_drift --check зелёный без skip-маркера. 3. Нормативные формулировки переведены как НОРМА, а не пересказ: QG-2, оценка в вызовах инструментов, роли, граница принуждения хуков. 4. i18n-strategy перестаёт противоречить себе: либо утверждение о полной локализации верно, либо исключение объявлено. 5. НЕГАТИВНЫЙ: перевод не расходится с русской половиной по числу разделов и по списку жёстких ограничений — сравнение по пунктам, а не на глаз. 6. Маркер unpaired снимается с русской половины вместе с появлением английской.

## Plan

## Rollback

## Journal
