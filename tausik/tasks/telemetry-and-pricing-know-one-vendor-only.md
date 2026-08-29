---
slug: telemetry-and-pricing-know-one-vendor-only
title: "Телеметрия понимает одну форму полезной нагрузки и цены одного вендора: на другой модели пишутся нули"
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
depends_on:
  - session-model-recorded-on-non-claude-hosts
completed_at: null
---

## Goal

ЗАМЕР #189. scripts/hooks/posttool_usage.py, функция _extract_usage, докстринг ДОСЛОВНО: «Anthropic-style extended schema may carry tool_response.usage or tool_response.message.usage with input_tokens / output_tokens. Older schemas don't expose this — return zeros + None.» То есть телеметрия умеет ОДНУ форму полезной нагрузки и на любой другой возвращает НУЛИ, не сказав ни слова.
СЛЕДСТВИЕ ДЛЯ КРОССМОДЕЛЬНОСТИ: TAUSIK раскладывается в пять профилей и заявлен как фреймворк для агентов, а не для одного вендора. На хосте с другой моделью tasks.cost_actual_usd и tokens_actual остаются нулями, и это неотличимо от «работа ничего не стоила». Бюджет по стоимости не срабатывает, калибровка считает по пустоте, метрики печатают ноль как факт.
ВТОРАЯ ПОЛОВИНА ТОГО ЖЕ ДЕФЕКТА — ЦЕНЫ. scripts/cost_pricing.py знает только семейство claude (claude-opus-*, claude-sonnet-*, claude-haiku-*, fable) плюс ключи free и unknown. Для любой другой модели стоимость либо ноль, либо unknown, и различить их снаружи нельзя.
ЧТО ДЕЛАЕТСЯ: (1) извлечение токенов становится набором АДАПТЕРОВ по форме полезной нагрузки, а не одной веткой под одного вендора; неизвестная форма даёт ЯВНОЕ «не смог прочитать», а не ноль; (2) таблица цен получает записи для моделей других вендоров и, главное, отличает «цена неизвестна» от «бесплатно» на уровне данных, а не на уровне надежды; (3) метрики и бюджеты обязаны показывать «не измерено» вместо нуля.
НЕГАТИВНОЕ, ГЛАВНОЕ: ноль и «неизвестно» — РАЗНЫЕ утверждения, и смешивать их нельзя ровно по той же причине, по которой в этом релизе «не выполнился» перестал быть «прошёл». Проверять двусторонне: неизвестная форма даёт явный отказ И известная форма по-прежнему читается.
СМЕЖНОЕ: usage-attribution-is-keyed-by-task-not-session (1.10) — там про КЛЮЧ атрибуции, здесь про СОДЕРЖИМОЕ. Не сливать.

## Acceptance Criteria

## Plan

## Rollback

Адаптеры извлечения плюс записи цен. Откат — git revert; собранные события остаются, повторный разбор не требуется.

## Journal

- 2026-08-29T13:57:38Z [planning] — [#189] ПЕРЕСЕЧЕНИЕ: ext-p1-provider-refactor, пункт G6 — «session model recording for non-Claude hosts (TAUSIK_AGENT_MODEL) so cost/pinning survive under GLM». Это ровно половина данной задачи (запись модели на не-Claude хосте), и она заведена там раньше. Не дублировать: здесь делается разбор ФОРМЫ полезной нагрузки и таблица цен по вендорам, там — механизм записи модели хостом. При взятии любой из двух свериться со второй. Дополнительно замерено, что задача zai-claude-code-firstclass закрылась со строкой cost: actual=$0.0000 / tokens: actual=0 — то есть нули писались уже тогда, в задаче ПРО GLM.
- 2026-08-29T14:22:55Z [planning] — [#189] ПОПРАВКА К ССЫЛКЕ: задача ext-p1-provider-refactor, упомянутая выше, УДАЛЕНА 29.08 после расщепления на четыре оценённые задачи (provider-generates-artifacts-not-the-if-ide-ladder, four-ide-registries-collapse-into-one, session-model-recorded-on-non-claude-hosts, bundled-root-separate-from-vendored-copy). Ссылка сохранена как происхождение формулировок, а не как указатель на живую задачу — искать её в базе бесполезно. Найдено собственной проверкой плана: это ровно тот класс сгнившей ссылки, который чинит audit evidence.
