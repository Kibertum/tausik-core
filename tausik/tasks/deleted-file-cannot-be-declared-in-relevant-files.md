---
slug: deleted-file-cannot-be-declared-in-relevant-files
title: "Удалённый файл невозможно объявить в relevant_files: гейт ruff падает на нём, а не объявить — значит занизить объём"
status: planning
epic: release-19-renar-conformance
story: gates-declare-what-they-prevent
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths:
  - "scripts/service_gates.py"
  - "scripts/gate_runner*.py"
  - "tests/test_gates.py"
  - "tests/test_verify_scope_honesty.py"
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

НАЙДЕНО НА ЖИВОЙ РАБОТЕ, смена #235, при закрытии ag-claims-and-docs-checked-against-the-graph.

ЧТО ПРОИСХОДИТ. Задача удалила файл (tests/test_doctor_doc_covers_every_check.py, чей предмет переехал в гейт). При закрытии объём объявляется через --relevant-files, и удалённый файл в него ВХОДИТ: он изменён задачей. Но гейт ruff получает список путей и пытается открыть каждый:

  [FAIL] ruff (block)
         E902 Не удается найти указанный файл. (os error 2)
         --> tests\test_doctor_doc_covers_every_check.py:1:1

Прогон возвращает exit=1 и НЕ выдаёт handle. То есть объявить удаление честно нельзя.

ЧЕМ ЭТО ПЛОХО, И ПОЧЕМУ ЭТО НЕ КОСМЕТИКА. Обходной путь один — не объявлять удалённый файл, и тогда verify честно печатает «1 file(s) changed since task start but not declared in relevant_files. The receipt records this — its coverage is narrower than the change». Иными словами, фреймворк ВЫНУЖДАЕТ занизить объявленный объём, а занижение объёма — ровно то, что замерено в 844 прогонах из 2265 (37%) и внесено в расширение объёма 1.9 решением #348 как предмет починки. Механизм, который сам толкает к занижению, обесценивает замер.

ПРЕДПОЛАГАЕМАЯ ПРИЧИНА: подстановка {files} в команду гейта не отличает существующий путь от удалённого. Файловые гейты (ruff, pytest, hadolint) должны получать только СУЩЕСТВУЮЩИЕ пути, тогда как объявление объёма и квитанция обязаны сохранять полный список, включая удаления — иначе receipt перестанет описывать изменение.

ГРАНИЦА: чинить надо в резолвере файлов гейта, а не в объявлении объёма. Объявление верно; неверно то, что делает с ним исполнитель гейта.

## Acceptance Criteria

## Plan

## Rollback

git revert. Изменение касается фильтрации путей перед запуском файловых гейтов; откат возвращает нынешнее поведение, при котором удалённый файл роняет ruff.

## Journal
