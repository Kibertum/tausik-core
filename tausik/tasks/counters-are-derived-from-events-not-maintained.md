---
slug: counters-are-derived-from-events-not-maintained
title: "Счётчики ёмкости и чекпоинта ведутся рядом с журналом, хотя выводятся из него"
status: planning
epic: release-110-deferred-from-19
story: deferred-110-architecture-and-research
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on:
  - usage-attribution-is-keyed-by-task-not-session
completed_at: null
---

## Goal

ПЕРЕНОС ФАКТОРА 5 (12-factor agents): объединить состояние ИСПОЛНЕНИЯ с состоянием предметной области и ВЫВОДИТЬ первое из журнала, а не вести рядом. Дословное предостережение фактора — не держать «сложные абстракции, отслеживающие то же самое отдельно».
У НАС ВЕДЁТСЯ ОТДЕЛЬНО: meta.tool_call_count (счётчик чекпоинта), счётчик ёмкости сессии (200 вызовов), активное время (180 мин). При этом usage_events уже несёт tool_calls, task_slug и recorded_at — то есть все три величины ВЫВОДИМЫ. Отдельное ведение уже давало рассинхрон: сохранение handoff обнуляло счётчик чекпоинта как побочный эффект (чинилось в 1.8, задача v2-session-split-and-drop).
ЧТО ДЕЛАЕТСЯ: счётчики становятся ЗАПРОСОМ к событиям, а не полем. Заодно снимается вопрос «что делать с гейтом ёмкости, когда сессия перестанет быть обязательной»: бюджет считается по активной ЗАДАЧЕ (call_budget уже есть и откалиброван, факт/бюджет 1.12 на n=10).
НЕГАТИВНОЕ: гейт, потерявший опору, обязан сказать это ВСЛУХ. Ровно этот дефект уже ловили — check_session_capacity возвращался рано при отсутствии сессии и переставал гейтить молча (fail-open). Повторить его при переносе будет вдвойне стыдно.
ЗАВИСИТ от атрибуции по задаче.

## Acceptance Criteria

## Plan

## Rollback

Замена полей на запросы; поля остаются в схеме до подтверждения. Откат — git revert.

## Journal
