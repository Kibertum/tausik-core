---
slug: renar-conformance-py-has-one-line-of-headroom
title: "renar_conformance.py: 499 строк при пределе 500 — запас в одну строку"
status: planning
epic: null
story: null
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

ЗАМЕР ПОДТВЕРЖДЁН (#210): scripts/renar_conformance.py = 499 строк, гейт filesize режет на 500.
В #210 гейт УЖЕ ОТКЛОНИЛ закрытие задачи: заменяя одну строку запроса, я развернул её на шесть (комментарий плюс форматирование вызова) и получил 504. Пришлось снимать комментарий и схлопывать вызов обратно, то есть ПОТЕРЯТЬ пояснение ради строк. Знание ушло в CHANGELOG и в докстринг миграции v50 — места, где ему есть место, — но следующая правка упрётся так же.
ЭТО НЕ ГИПОТЕТИЧЕСКИЙ ДОЛГ: он уже стоил одной итерации закрытия и назван в передаче #209 как «НЕ ЗАВЕДЕНО». Заводится сейчас, чтобы перестать кочевать.
ПОЧИНКА: вынести связную часть в отдельный модуль по образцу того, как backend_schema_adapts.py вынесен из backend_schema.py ради того же гейта. Естественный кандидат — блок сборки манифеста §13.4.2 (manifest-id, replaces, replaced-by), он же предмет задачи conformance-replaces-default-derived-from-a-date; делать эти две подряд дешевле, чем порознь.
ВНЕ ОБЪЁМА 1.9 НАМЕРЕННО: это техдолг размера файла, а не долг по норме RENAR. Если владелец решит иначе — перенести в историю.

## Acceptance Criteria

## Plan

## Rollback

## Journal
