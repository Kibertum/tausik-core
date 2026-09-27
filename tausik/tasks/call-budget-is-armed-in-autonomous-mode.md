---
slug: call-budget-is-armed-in-autonomous-mode
title: "call_budget становится жёстким стопом в автономном режиме, а не советом"
status: planning
epic: release-110-deferred-from-19
story: release110-open-defects
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 35
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

ВТОРАЯ ИЗ ПЯТИ ЗАДАЧ АВТОНОМНОСТИ (ревью смены #277).

ЗАМЕР: за смену я пробил call_budget три раза — 106 против 40, 124 против 70, 139 против 90. Каждый раз предупреждение печаталось ПОСЛЕ закрытия, то есть узнать о перерасходе можно было только когда он уже случился.

У kiberza это решено, и решение стоит взять: скилл /run экспортирует KAI_AUTONOMOUS_BUDGET_BLOCK=1 на время батча и после каждого закрытия проверяет `task budget-check` по слагу; ненулевой выход равен отказу и останавливает прогон. Интерактивная работа при снятом флаге не меняется — совет остаётся советом.

ПОЧЕМУ БЕЗ ЭТОГО НЕЛЬЗЯ ЗАПУСКАТЬ ДРАЙВЕР: неприсмотренный прогон с советом вместо потолка сожжёт смену на одной задаче и остановится не по плану, а по исчерпанию. Владелец узнает об этом утром.

ПРОВЕРИТЬ ПЕРВЫМ: есть ли в core эквивалент `task budget-check` или его надо заводить; и на каком множителе ставить потолок — у kiberza 2×, и это число надо либо взять с обоснованием, либо замерить по своим закрытиям.

## Acceptance Criteria

## Plan

## Rollback

## Journal
