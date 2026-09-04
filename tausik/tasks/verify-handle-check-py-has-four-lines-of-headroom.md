---
slug: verify-handle-check-py-has-four-lines-of-headroom
title: "verify_handle_check.py: 496 строк при пределе 500 — ревью советовало разделить заранее"
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

ЗАМЕР ПОДТВЕРЖДЁН (#210): scripts/verify_handle_check.py = 496 строк при пределе 500.
Ревью в #209 назвало это low и посоветовало разделить ЗАРАНЕЕ, а не под давлением закрытия. Совет не исполнен, задача не заводилась, пункт кочует передачами.
ЗАЧЕМ ЗАРАНЕЕ, А НЕ ПО ФАКТУ. Разделение под давлением гейта делается в худший момент: правка уже написана, тесты уже зелёные, и единственное, чего хочется, — вернуть строки любой ценой. Ровно это произошло в #210 с соседним файлом renar_conformance.py: пояснение было снято, чтобы влезть в предел, и решение принималось не по существу, а по остатку строк. Файл на 496 даёт следующему автору четыре строки — меньше, чем занимает один осмысленный комментарий с вызовом.
ВНЕ ОБЪЁМА 1.9 НАМЕРЕННО: техдолг размера, не долг по норме.

## Acceptance Criteria

## Plan

## Rollback

## Journal
