---
slug: final-tz-is-the-acceptance-reference-and-we-have-none
title: "Итоговое ТЗ — эталон сдачи-приёмки: у нас нет ни его, ни правила приоритета"
status: planning
epic: release-19-renar-conformance
story: renar-contract-contour
complexity: null
role: architect
stack: python
tier: substantial
call_budget: 100
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

RENAR §5A.4: итоговое ТЗ есть начальное ТЗ с приложениями ПЛЮС все подписанные ACTZ, и приоритет принадлежит более позднему подписанному документу. ADAPT в эталон приёмки не входит — именно это делает приёмку юридически чистой. Из этого следуют два правила, которых у нас нет: подписанное решение, не отражённое ни в одном ADAPT, есть обязательство вне требований и классифицируется как fatal; интерпретация не имеет права опираться на решение, которого клиент не принимал. Задача: вычислять итоговое ТЗ как производное представление (не третью копию текста), уметь показать его на любой момент времени и назвать, какой ACTZ какой пункт перекрыл. Отдельно — обнаружение того самого fatal: подписанный пункт без ссылающегося ADAPT обязан находиться запросом, а не глазами. Зависит от actz-the-contract-contour-artifact-is-missing.

## Acceptance Criteria

## Plan

## Rollback

## Journal
