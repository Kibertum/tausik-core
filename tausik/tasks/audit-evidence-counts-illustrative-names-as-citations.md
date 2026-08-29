---
slug: audit-evidence-counts-illustrative-names-as-citations
title: "audit evidence считает иллюстративные имена из прозы сгнившими ссылками: корзина NEVER_EXISTED в основном шум"
status: planning
epic: null
story: null
complexity: simple
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

НАЙДЕНО ПЕРВЫМ БОЕВЫМ ПРОГОНОМ КОМАНДЫ В #189 (dogfooding: команда приехала в 82b8ed7, это её первое применение по всей базе).

ЗАМЕР: 1239 закрытых задач, 515 ссылаются на тест, 2756 ссылок / 1009 уникальных, разрешаются сегодня 968, ROTTED 16, NEVER_EXISTED 25, UNKNOWN_HISTORY 0.

ДЕФЕКТ В КОРЗИНЕ NEVER_EXISTED. Значительная её часть — не сгнившие ссылки, а ИЛЛЮСТРАТИВНЫЕ ИМЕНА, процитированные в ПРОЗЕ задачи. Проверено чтением исходных записей:
- rule5-checklist-keyword-theater: «(3) Несуществующий артефакт — ::test_unresolvable_test_reference_is_treated_as_no_evidence, ссылка на tests/test_does_not_exist.py даёт block=True (fail-closed)». Файл НАЗВАН так, чтобы не существовать: это описание отрицательного сценария, а не доказательство закрытия.
- closure-evidence-references-rot-and-nothing-notices: «✓ MANUAL на живых данных: tests/foo.py, tests/test_x.py, tests/test_does_not_exist.py, tests/unit/scoped/test_bar.py» — перечень ВХОДНЫХ ДАННЫХ ручной проверки самой этой команды.
Из тринадцати видимых в хвосте отчёта записей примерно десять такого рода: tests/test_X.py, tests/test_a.py, tests/test_file.py, tests/test_foo.py, tests/test_foo.py::test_bar, tests/test_real.py::test_a, tests/test_x.py, tests/x.py, tests/unit/scoped/test_bar.py, tests/test_does_not_exist.py. Настоящих находок в той же корзине как минимум две: tests/test_ble001_enforced.py::test_ble001_selected_in_pyproject (кандидат-преемник test_ble001_enabled_in_config) и tests/test_knowledge_export.py::TestTheDestinationMustBeLocal (кандидат TestRemoteDestinationsAreRefused) — это настоящие переименования.

ПОЧЕМУ ЭТО ВАЖНО, А НЕ КОСМЕТИКА. Отчёт, где большинство записей в корзине — шум, обучает читателя пролистывать корзину. Это ровно класс doctor-warns-forever-about-a-deliberate-verify-profile: сигнал, не несущий решения, обесценивает соседние сигналы, которые его несут. Здесь цена выше: рядом лежат 16 ROTTED — настоящие сгнившие ссылки на доказательства закрытия.

ЧТО ДЕЛАТЬ (форму выбрать замером, а не вкусом): извлекать ссылку не отовсюду, а из строк доказательства («AC-N: ✓ путь::имя» и эквивалентов), либо помечать цитату в прозе отдельной корзиной ILLUSTRATIVE, либо и то и другое. НЕГАТИВНОЕ, ДВУСТОРОННЕЕ: настоящая сгнившая ссылка обязана остаться в ROTTED (проверить на tests/test_ble001_enforced.py::test_ble001_selected_in_pyproject), а иллюстративная — уйти из NEVER_EXISTED (проверить на tests/test_does_not_exist.py). Обе стороны, иначе «починка» окажется глушилкой.

ОГОВОРКА: команда read-only и никогда не блокирует — дефект не мешает закрытиям, он портит только отчёт. Поэтому это гигиена сигнала, а не срочность.

## Acceptance Criteria

## Plan

## Rollback

Правка в извлечении ссылок команды audit evidence (read-only, ничего не блокирует). Откат — git revert; данные не изменяются, отчёт пересчитывается каждым прогоном.

## Journal
