---
slug: session-model-recorded-on-non-claude-hosts
title: "Модель сессии не записывается на не-Claude хостах: стоимость и пиннинг молчат под GLM"
status: planning
epic: release-19-renar-conformance
story: guarantees-are-not-claude-only
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
depends_on: []
completed_at: null
---

## Goal

РАСЩЕПЛЕНИЕ ext-p1-provider-refactor (цель G6), выполнено в #189.
ФОРМУЛИРОВКА ИЗ ИСХОДНОЙ ЗАДАЧИ: «session model recording for non-Claude hosts (TAUSIK_AGENT_MODEL) so cost/pinning survive under GLM».
ЗАМЕР, ДОКАЗЫВАЮЩИЙ НУЖДУ (#189): задача zai-claude-code-firstclass — та самая, что делала GLM первоклассным путём, — закрылась со строкой `cost: actual=$0.0000 / tokens: actual=0`. Модель не записана, стоимость не посчитана, пиннинг (started_model_id / done_model_id / model_mismatch) не сработал. То есть на флагманском не-Anthropic пути телеметрия молчит с самого его появления.
ЧТО ДЕЛАЕТСЯ: хост, не сообщающий модель сам, объявляет её переменной окружения TAUSIK_AGENT_MODEL; фреймворк записывает её в сессию и задачу; отсутствие значения даёт ЯВНОЕ «модель не объявлена», а не молчаливый NULL.
СВЯЗЬ: telemetry-and-pricing-know-one-vendor-only разбирает ФОРМУ полезной нагрузки и таблицу цен; здесь — источник самого имени модели. Обе нужны, ни одна не заменяет другую.
НЕГАТИВНОЕ: не выводить модель из имени хоста. Claude Code с ANTHROPIC_BASE_URL на z.ai — это GLM, а не Claude, и именно этот случай мы обязаны различать.

## Acceptance Criteria

## Plan

## Rollback

Чтение переменной окружения и запись поля; откат git revert, поля остаются пустыми как сейчас.

## Journal

- 2026-08-29T14:22:54Z [planning] — [#189] ПОПРАВКА К ССЫЛКЕ: задача ext-p1-provider-refactor, упомянутая выше, УДАЛЕНА 29.08 после расщепления на четыре оценённые задачи (provider-generates-artifacts-not-the-if-ide-ladder, four-ide-registries-collapse-into-one, session-model-recorded-on-non-claude-hosts, bundled-root-separate-from-vendored-copy). Ссылка сохранена как происхождение формулировок, а не как указатель на живую задачу — искать её в базе бесполезно. Найдено собственной проверкой плана: это ровно тот класс сгнившей ссылки, который чинит audit evidence.
