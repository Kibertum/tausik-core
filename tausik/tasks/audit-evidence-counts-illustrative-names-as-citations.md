---
slug: audit-evidence-counts-illustrative-names-as-citations
title: "audit evidence считает иллюстративные имена из прозы сгнившими ссылками: корзина NEVER_EXISTED в основном шум"
status: done
epic: release-19-renar-conformance
story: standards-drift-detection
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: "Ничего не правится этой задачей: её предмет реализован корневой задачей memory-lint-flags-absent-path-that-is-the-memorys-subject, которая чинила ОБА детектора одним понятием. Задача закрывается предъявлением того же доказательства."
scope_exclude: "Никаких новых правок кода: повторная частная реализация того же понятия в audit evidence и была бы дефектом, ради устранения которого корневая задача написана."
relevant_files:
  - "scripts/illustrative_paths.py"
  - "scripts/audit_closure_evidence.py"
  - "scripts/project_cli_audit.py"
  - "tests/test_illustrative_paths.py"
  - "tests/test_audit_closure_evidence.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-09-04T10:23:48Z"
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

AC-1: Иллюстративное имя из строки доказательства уходит из корзины NEVER_EXISTED в отдельную корзину, а число в шапке перестаёт врать.
AC-2 (негативный сценарий, двусторонний): настоящая сгнившая ссылка ОСТАЁТСЯ найденной — проверить на tests/test_ble001_enforced.py::test_ble001_selected_in_pyproject; иллюстративная УХОДИТ — проверить на tests/test_does_not_exist.py. Одна сторона без другой есть ошибка, а не починка: детектор, из которого убрали шум, неотличим от выключенного.
AC-3: Замер до и после предъявлен числами на живом корпусе.

## Plan

## Rollback

git revert <commit> корневой задачи memory-lint-flags-absent-path-that-is-the-memorys-subject. Команда read-only, данные не меняются, отчёт пересчитывается каждым прогоном.

## Journal

- 2026-09-04T10:23:16Z [implementation] — ЗАКРЫТА ПРЕДЪЯВЛЕНИЕМ ЧУЖОГО ДОКАЗАТЕЛЬСТВА, БЕЗ НОВЫХ ПРАВОК. Память #481 прямо предупреждала: под этот дефект уже заведена корневая задача memory-lint-flags-absent-path-that-is-the-memorys-subject (complex), чинящая ОБА детектора одним понятием, «на ОДИН корень, а не на два симптома». Реализовать здесь второй частный список заглушек означало бы воспроизвести ровно тот дефект, ради которого корневая задача написана. ПОПРАВКА К ОПИСАНИЮ ЭТОЙ ЗАДАЧИ. Она утверждала, что ссылки извлекаются «из прозы задачи». Замер показал иное: extract_refs берёт их через service_ac_evidence.parse_evidence_lines, то есть ТОЛЬКО из строк доказательств; предложенный в описании вариант «извлекать не отовсюду, а из строк доказательства» был реализован ещё до задачи. Иллюстративные имена сидят ВНУТРИ самих строк доказательств (перечень входных данных ручной проверки после галочки). Поэтому починка легла на толкование ПУТИ внутри строки, а не на выбор строк. ЗАМЕР ДО: NEVER_EXISTED 25 при 3 настоящих находках, рядом ROTTED 22. ЗАМЕР ПОСЛЕ: NEVER_EXISTED 12, ILLUSTRATIVE 13, ROTTED 22 без изменений; у каждой записи в новой корзине напечатан сработавший признак. Все три настоящие находки остались в NEVER_EXISTED. Negative: обе стороны проверены на живом корпусе и закреплены тестами — tests/test_audit_closure_evidence.py::test_a_genuine_miss_is_not_moved_into_the_example_bucket (настоящая остаётся) и tests/test_audit_closure_evidence.py::test_an_example_name_gets_its_own_verdict (иллюстративная уходит). Ошибкой считается любой односторонний исход. AC-1: ✓ tests/test_audit_closure_evidence.py::test_an_example_name_gets_its_own_verdict AC-2: ✓ tests/test_audit_closure_evidence.py::test_a_genuine_miss_is_not_moved_into_the_example_bucket AC-3: ✓ tests/test_illustrative_paths.py::test_every_measured_example_is_recognised Domain: числа сняты не на фикстурах, а на 1304 закрытых задачах и 3299 цитатах живого корпуса; смысл различения в том, что путь с сегментом «..» или ведущим «./» указывает на файл относительно рабочего каталога команды, и утверждение «такого файла в репозитории нет» о нём не определено.
- 2026-09-04T10:24:05Z [done] — ГЕЙТ ПРАВ, ЗАПИСЫВАЮ ПРОТИВ СЕБЯ. COMPLEXITY UNDERSTATED: объявлено simple при пяти несущих файлах в relevant_files. Формально задача не изменила ни строки — файлы принадлежат корневой задаче, — но объявление и предъявленный набор разошлись, а гейт судит по набору и судит верно: закрытие, опирающееся на пять несущих файлов, не есть simple, чем бы ни объяснялось. ШЕСТАЯ СМЕНА ПОДРЯД ПО ПАМЯТИ #523. Правильно было объявить medium ДО старта. Урок узкий и новый: наследованная оценка задачи-симптома подлежит переоценке не только по своей работе, но и по РАЗМЕРУ ДОКАЗАТЕЛЬСТВА, которым её закрывают.
