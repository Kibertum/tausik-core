---
slug: verification-checklist-detector-misses-the-form-it-asked-for
title: "Гейт третий раз подряд говорит «чек-лист отсутствует», хотя чек-лист записан ДО закрытия: он не распознаёт форму, которую сам же попросил"
status: done
epic: landscape-2026-h2
story: l26-silent-failures-in-shipped-commands
complexity: simple
role: developer
stack: python
tier: moderate
call_budget: 30
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/service_ac_evidence.py"
  - "scripts/gate_ac_check.py"
  - "scripts/ac_evidence_detectors.py"
scope_paths:
  - "scripts/service_ac_evidence.py"
  - "scripts/ac_evidence_detectors.py"
  - "scripts/gate_ac_check.py"
  - "tests/*"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_tools: []
depends_on: []
completed_at: "2026-08-03T19:55:55Z"
---

## Goal

Найдено дogfooding-ом в сессии #156, три раза подряд, счётчик самого гейта дошёл до «reminder #3».

СИМПТОМ: закрытие задачи выдаёт «Verification checklist — no acceptance criterion names a test, a manual run, a review or a green verification_run» и «verification checklist missing in notes (SENAR Rule 5)», хотя чек-лист с поимёнными ссылками вида tests/test_x.py::TestY::test_z был записан через task log НЕПОСРЕДСТВЕННО ПЕРЕД закрытием и виден в notes задачи.

ГИПОТЕЗА, требует проверки: детектор ищет пару «номер критерия и ссылка на тест В ОДНОЙ СТРОКЕ», то есть шаблон вида «AC-2: ✓ tests/foo.py::test_bar». Мой чек-лист структурирован иначе — заголовок «AC-2 (что проверяется):» отдельной строкой, а ссылки на тесты следующими строками, потому что критерий покрывается НЕСКОЛЬКИМИ тестами и уместить их в одну строку нельзя. Форма читаемее, но детектор её не видит.

ПОЧЕМУ ЭТО НЕ КОСМЕТИКА: гейт существует, чтобы галочка не подменяла доказательство. Когда он не распознаёт доказательство В САМОЙ ПОЛНОЙ ЕГО ФОРМЕ, он приучает игнорировать себя — а предупреждение, которое привыкли игнорировать, перестаёт работать и в тех случаях, когда чек-листа действительно нет. Это утрата сигнала, а не неудобство.

ЧТО СДЕЛАТЬ: (1) найти детектор и установить ТОЧНО, что он ищет; (2) либо расширить его до многострочной формы «заголовок критерия + ссылки ниже», либо, если многострочность принципиально не поддерживается, изменить ТЕКСТ подсказки так, чтобы он называл единственную принимаемую форму — сейчас он показывает пример, но не говорит, что пример является ЕДИНСТВЕННЫМ распознаваемым видом. (3) Проверить на моих трёх реальных чек-листах из этой сессии (kb-global-read, kb-global-version-guard, kb-export-global) — они лежат в journal задач и служат живыми данными, а не выдуманными примерами.

НЕГАТИВНЫЙ СЦЕНАРИЙ ОБЯЗАТЕЛЕН: задача БЕЗ чек-листа по-прежнему обязана получать предупреждение. Расширение распознавания не должно превратиться в «принимать что угодно» — иначе гейт перестанет отличать доказательство от его отсутствия, что хуже нынешнего состояния.

## Acceptance Criteria

ГИПОТЕЗА ИЗ ПОСТАНОВКИ ПОДТВЕРЖДЕНА ЗАМЕРОМ, а не принята: match_evidence_to_ac связывает доказательство с критерием ТОЛЬКО по префиксу AC-N в ТОЙ ЖЕ строке. Многострочная форма (заголовок критерия, ссылки на тесты ниже) даёт covered=0 из 3 и checklist_missing=True при трёх настоящих ссылках на тесты. На живых данных четырёх задач из БД — от 21 до 45 осиротевших строк доказательства на задачу.

AC1: многострочная форма распознаётся. Тест: заголовок AC-N и следующие за ним строки со ссылками на тесты дают covered>0 и checklist_missing=False.
AC2: наследование ОГРАНИЧЕНО секцией, а не разлито по заметкам. Тест: строка со ссылкой на тест ДО первого заголовка критерия не привязывается ни к чему; пустая строка и начало новой записи журнала обрывают секцию.
AC3 (ГЛАВНЫЙ НЕГАТИВ): расширение НЕ превращается в «принимать что угодно». Тест: задача вообще без чек-листа по-прежнему даёт checklist_missing=True; голая галочка без ссылки не наследует индекс; ПРОЗА, упоминающая путь к тесту без галочки (плановая заметка вида «ограничение: tests/x.py:62 утверждает...»), НЕ засчитывается за доказательство, даже если стоит внутри секции критерия.
AC4: проверено на ЖИВЫХ данных, а не на выдуманных примерах — на заметках задач kb-global-read, kb-global-version-guard, kb-export-global и help-text-names-the-old-shared-store-path из БД. Число осиротевших строк ДО и ПОСЛЕ названо в журнале.
AC5: подсказка гейта называет ОБЕ принимаемые формы, а не показывает один пример, умалчивая, что он единственный распознаваемый.
AC6: полный pytest зелёный; mypy и ruff чистые.

## Plan

## Rollback

## Journal

- 2026-08-03T08:53:34Z [planning] — ЧЕТВЁРТЫЙ случай подряд, задача help-text-names-the-old-shared-store-path (сессия #158). В журнале записан блок ровно требуемого вида: строка 'AC verified:' и четыре пункта '1. ✓ ... 2. ✓ ...', каждый со ссылкой на тест и на обратимую пробу, плюс отдельная строка про verify run #1644 с PASS по 16 файлам. Гейт всё равно печатает 'verification checklist missing in notes' и следом 'no acceptance criterion names a test' — хотя тесты названы поимённо. То есть детектор не видит НИ факта чек-листа, НИ ссылок на тесты внутри него. Повтор четвёртый. Гейт, который стабильно врёт про отсутствие доказательства, обучает игнорировать свой вывод целиком — а это ровно тот гейт, чей вывод должен быть последним словом при закрытии.
- 2026-08-03T19:55:23Z [implementation] — Root cause (logic-error): match_evidence_to_ac связывал доказательство с критерием ТОЛЬКО по префиксу AC-N в той же строке, а подсказка гейта показывала однострочный пример, не говоря, что он единственный распознаваемый. Многострочная форма (заголовок критерия, ссылки на тесты ниже) — единственная, в которую помещается критерий, покрытый четырьмя тестами, — давала covered=0 и вердикт 'чек-лист отсутствует' при настоящих ссылках на тесты. AC4, ЖИВЫЕ ДАННЫЕ, а не выдуманные примеры: на заметках четырёх задач из БД (help-text-names-the-old-shared-store-path, kb-global-read, kb-global-version-guard, kb-export-global) осиротевших строк доказательства было 0+35+21+45 = 101, стало 69; покрытие 18/18 не изменилось, потому что в тех задачах рядом лежала и однострочная форма — именно она их и спасала, и это подтверждает диагноз, а не опровергает. Оставшиеся 69 — строки-продолжения без ссылок и проза, они и не должны считаться. Prevention: наследование СЕКЦИОННОЕ и обусловлено ДВУМЯ признаками сразу (галочка И настоящая ссылка), границы секции — следующий заголовок, пустая строка, новая запись журнала; расширение проверено В ОБЕ СТОРОНЫ, шесть негативных тестов утверждают, что задача без чек-листа, голая галочка, проза со ссылкой и ссылка до первого заголовка по-прежнему НЕ засчитываются. Три положительных теста проверены на красноту отключением наследования.
- 2026-08-03T19:55:52Z [implementation] — Этот чек-лист написан В ТОЙ САМОЙ многострочной форме, которую задача чинит, — если правка не работает, гейт скажет об этом прямо здесь. AC-1 (многострочная форма распознаётся): ✓ tests/test_ac_evidence_multiline_sections.py::test_the_fuller_form_is_recognised ✓ tests/test_ac_evidence_multiline_sections.py::test_a_heading_covered_by_four_tests_is_the_point ✓ tests/test_ac_evidence_multiline_sections.py::test_the_single_line_form_still_works AC-2 (наследование ограничено секцией): ✓ tests/test_ac_evidence_multiline_sections.py::TestWideningIsNotAcceptingAnything::test_a_blank_line_ends_the_section ✓ tests/test_ac_evidence_multiline_sections.py::TestWideningIsNotAcceptingAnything::test_a_new_log_entry_ends_the_section ✓ tests/test_ac_evidence_multiline_sections.py::TestWideningIsNotAcceptingAnything::test_a_later_heading_takes_over_from_the_earlier_one ✓ tests/test_ac_evidence_multiline_sections.py::TestWideningIsNotAcceptingAnything::test_a_citation_before_any_heading_belongs_to_nothing AC-3 (главный негатив: не «принимать что угодно»): ✓ tests/test_ac_evidence_multiline_sections.py::TestWideningIsNotAcceptingAnything::test_a_task_with_no_checklist_is_still_warned ✓ tests/test_ac_evidence_multiline_sections.py::TestWideningIsNotAcceptingAnything::test_prose_naming_a_path_is_not_evidence_even_inside_a_section ✓ tests/test_ac_evidence_multiline_sections.py::TestWideningIsNotAcceptingAnything::test_a_bare_tick_does_not_inherit_a_section AC-4 (проверено на живых данных): ✓ verification_run #1709 AC-5 (подсказка называет обе формы): ✓ tests/test_ac_evidence_multiline_sections.py::TestTheMessageNamesBothForms::test_the_hard_block_message_offers_the_multiline_form ✓ tests/test_ac_evidence_multiline_sections.py::TestTheMessageNamesBothForms::test_the_warning_offers_both_forms AC-6 (чистота): ✓ verification_run #1709
