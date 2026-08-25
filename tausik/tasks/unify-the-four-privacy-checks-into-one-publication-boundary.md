---
slug: unify-the-four-privacy-checks-into-one-publication-boundary
title: "[1.9] Свести четыре проверки приватности к одной границе публикации"
status: planning
epic: shared-knowledge
story: kb-notion
complexity: medium
role: architect
stack: python
tier: moderate
call_budget: 60
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

Вынесено из kb-brain-deprecate решением #221. В 1.8 снимается классификатор с РЕШЕНИЯ о публикации (это останавливает утечку); свести оставшиеся проверки в одну границу — работа архитектурная и в бюджет 1.8 не входит.

ЧЕТЫРЕ ТОЧКИ, названы карточкой-предшественницей и подтверждены разведкой:
1. маршрутизация в service_knowledge.decide (СНИМАЕТСЯ в 1.8 решением #221),
2. второй прогон того же classify внутри brain_publish_flow.assess_publish_risk,
3. scrub_inputs в brain_mcp_write.store_record,
4. гард принадлежности БД is_working_project_db в service_decide.

ПОСЛЕ 1.8 ОСТАНЕТСЯ ТРИ, и это уже лучше четырёх, но всё ещё три места, где независимо решается один вопрос. Задача — свести их к одной функции-границе.

ПОКРЫТИЕ ДОКАЗЫВАТЬ СВОЙСТВОМ, А НЕ ПЕРЕЧНЕМ (конвенция #354): всякий путь наружу проходит через единственную функцию. Перечень точек вызова устаревает молча — это в проекте уже случалось.

ГОТОВЫЙ ОБРАЗЕЦ ЕСТЬ: tests/test_notion_is_optional.py::test_no_content_reaches_notion_outside_the_scrubbed_funnel уже проверяет свойство рекурсивно по scripts/ и harness/, по трём методам записи клиента, с аллоулистом исключений С ПРИЧИНОЙ. Расширять надо его, а не писать второй.

НЕГАТИВНЫЙ СЦЕНАРИЙ ОБЯЗАТЕЛЕН: после объединения запись, которую публиковать НЕЛЬЗЯ, по-прежнему не публикуется — и тест обязан подавать вход, который прежние проверки ловили ПО ОТДЕЛЬНОСТИ, чтобы объединение не потеряло одну из них молча.

## Acceptance Criteria

## Plan

## Rollback

## Journal
