---
slug: at-acceptance-tests-derived-by-an-isolated-agent
title: "AT — приёмочный тест от контракта: выводится изолированным агентом и перегенерируется перед испытаниями"
status: planning
epic: release-19-renar-conformance
story: renar-contract-contour
complexity: null
role: architect
stack: python
tier: substantial
call_budget: 150
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

RENAR §8A (ADR-012, accepted). Прослеживаемость TC замкнута через интерпретацию: TC → SR → ADAPT → ТЗ. Отсюда класс дефектов, который TC не ловит В ПРИНЦИПЕ: при неверной интерпретации ВСЕ TC зелёные, потому что система идеально соответствует неверному толкованию — и проваливает приёмку у заказчика. AT закрывает ровно этот остаток и только его. Три обязательных свойства: (1) выводится ИЗОЛИРОВАННЫМ агентом исключительно из итогового ТЗ, без доступа к ADAPT, BR, SR, SPEC, TC и коду; (2) ПЕРЕГЕНЕРИРУЕТСЯ перед каждыми испытаниями от действующей редакции, иначе система в конце длинного заказа проверяется против контракта годичной давности; (3) обязательное поле tz_text — дословная цитата пункта контракта. Изоляция здесь не пожелание, а механизм генерации: агент, видевший интерпретацию, воспроизведёт её ошибку. У нас уже есть внешний ревьюер на другой модели — механизм разделения обязанностей существует, но для AT нужна изоляция ПО ВХОДУ, а не только по автору. Зависит от final-tz-is-the-acceptance-reference-and-we-have-none.

## Acceptance Criteria

## Plan

## Rollback

## Journal
