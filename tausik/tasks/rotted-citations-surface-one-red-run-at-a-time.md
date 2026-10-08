---
slug: rotted-citations-surface-one-red-run-at-a-time
title: "Гнилая цитата на тест находится по одной за прогон вместо всех сразу"
status: done
epic: release-110-deferred-from-19
story: deferred-110-audit-hygiene
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths:
  - "scripts/"
  - "tests/"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-09-29T16:57:39Z"
resolution: obsolete
resolution_reason: "Отменена замером, а не отложена. Предпосылка «цитаты гниют в нескольких местах, и их надо собрать вместе» верна, но сборщик на живом дереве даёт 405 находок, из которых почти все законные: выдуманные имена в тестах про цитаты, история CHANGELOG, чужой чекаут. Настоящий сигнал — только tausik/gates.json, одно место из двух. Дешёвый ответ без кода: grep по старому имени после переименования. Записано тупиком #801; модуль scripts/repo_coherence_citations.py удалён, регистрация в repo_coherence снята."
tracker_refs: []
started_model_id: claude-opus-5
started_model_version: null
done_model_id: null
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
---

## Goal

Переименование теста ломает цитаты на него в нескольких местах сразу — red_proofs в tausik/gates.json, таблица EXCUSED в tests/test_gates_catch_their_violation.py, evidence закрытых задач. Каждая всплывает ОТДЕЛЬНЫМ красным прогоном, и каждый стоит вызов: при 482 000 токенов префикса это около полумиллиона за штуку. Замер смены #278: две такие находки на одной задаче, два отдельных прогона. Цель: одна команда разрешает ВСЕ цитаты репозитория и называет каждую гнилую разом.

## Acceptance Criteria

AC-1 Сборщик в tausik coherence разрешает КАЖДУЮ цитату вида <путь>.py::<имя> где бы она ни стояла в дереве — в tausik/gates.json, в таблицах внутри tests/, в скриптах. Цитаты закрытых задач НЕ дублируются: их уже покрывает сборщик closure_evidence, и второй счёт того же был бы двумя правдами об одном числе. ✓ tests/test_citation_resolution_collector.py
AC-2 Находка называет КАЖДУЮ неразрешимую цитату с файлом, где она написана, и с именем, которого нет, а не только их число.
AC-3 НЕГАТИВНЫЙ: подложенная гнилая цитата ловится на подложенном дереве — и в JSON, и в Python-файле.
AC-4 НЕГАТИВНЫЙ: нечитаемый или отсутствующий источник даёт ОТСУТСТВИЕ с причиной, а не ноль находок (решение #334).
AC-5 НЕГАТИВНЫЙ: строка, похожая на цитату, но не являющаяся ею (путь вне дерева тестов, имя без префикса test_), НЕ считается находкой — иначе сборщик приезжает шумным и его выключают.
AC-6 На живом дереве находок нет.
AC-7 Полная лента зелёная.

## Plan

## Rollback

git revert; coherence возвращается к четырём сборщикам

## Journal
