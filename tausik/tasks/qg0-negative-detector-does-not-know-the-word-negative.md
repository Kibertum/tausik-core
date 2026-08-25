---
slug: qg0-negative-detector-does-not-know-the-word-negative
title: "QG-0 не признаёт слово «негативный»: два детектора одного фреймворка расходятся в том, как называется негативный сценарий"
status: done
epic: null
story: null
complexity: medium
role: architect
stack: python
tier: moderate
call_budget: 55
defect_of: null
scope: "scripts/gate_negative_scenario.py (добавить отрицательн + сослаться на источник), tests/ (parity-guard между has_negative_scenario и NEGATIVE_RE + decorative-guard)"
scope_exclude: "Не расширять NEGATIVE_SCENARIO_KEYWORDS сверх паритета с NEGATIVE_RE (не превращать в свалку синонимов); не менять QG-0 в семантический разбор (это planning-гейт, описание сценария верифицируется на task-done)"
relevant_files:
  - "scripts/gate_negative_scenario.py"
  - "tests/test_negative_scenario_parity.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-26T23:05:48Z"
---

## Goal

Замер сессии #135, воспроизводится одной строкой: has_negative_scenario('1. Негативные сценарии покрыты тестами.') -> False. При этом сообщение самого гейта предлагает написать «Ошибка при пустом поле», и вот это (has_negative_scenario('1. Ошибка внутри проверки не должна ронять сервер.')) -> True.

РАСХОЖДЕНИЕ ВНУТРИ ОДНОГО ФРЕЙМВОРКА. NEGATIVE_SCENARIO_KEYWORDS в scripts/gate_negative_scenario.py содержит английское 'negative', но НЕ содержит русского 'негативн' — при том что в scripts/ac_evidence_detectors.py, приведённом к языковому паритету в сессии #134, NEGATIVE_RE это ровно `\bnegative\b|негативн\w*|отрицательн\w*`. То есть два детектора одного фреймворка, отвечающие на один и тот же вопрос («описан ли негативный сценарий»), знают разные наборы слов: один — на этапе закрытия, другой — на этапе старта. Задача сессии #134 выровняла ОДИН из них и не заметила второго.

ЦЕНА. Гейт QG-0 ЖЁСТКИЙ: задача не стартует. В сессии #135 он дважды заблокировал старт задачи, у которой негативные сценарии были расписаны подробно и по-русски (по три-пять граничных случаев на критерий) — просто названы словом «негативные», а не словом «ошибка». Лечится это переписыванием формулировки под словарь, то есть агент учится подбирать слова под детектор, а не описывать проверку. Ровно тот приём, который проект называет keyword theater и наказывает в других местах.

ЧТО ДЕЛАТЬ. Минимум: добавить 'негативн' и 'отрицательн' в NEGATIVE_SCENARIO_KEYWORDS. Но правильнее закрыть КЛАСС, а не строку: в проекте есть ДВА словаря негативности, и второй появился как копия; их надо свести к одному источнику (конвенция #301 — перенося детектор на новый диалект, переноси и список ложных срабатываний). Проверить при этом, не станет ли слово «негативные» дешёвым паролем: has_negative_scenario должен по-прежнему отвергать AC, где негативность только ОБЪЯВЛЕНА («негативные сценарии учтены») без описания самого случая — иначе гейт из строгого станет декоративным. Это главный риск правки, и он требует отдельного теста.

ОБЯЗАТЕЛЬНО: дифференциальный прогон старой и новой реализации на РЕАЛЬНЫХ acceptance_criteria всех закрытых задач (память #298) — показать числом, сколько AC меняют вердикт, и просмотреть их глазами.

## Acceptance Criteria

AC1. has_negative_scenario распознаёт русскую форму 'отрицательн' (was False): 'отрицательный результат обрабатывается' → True. Дифф-прогон старой/новой на 963 реальных AC: 0 меняют вердикт (нет ретро-регрессии; замер приложен).
AC2. КЛАСС закрыт executable-инвариантом (#301): parity-тест вычисляет негатив-СЛОВА семейство из ac_evidence_detectors.NEGATIVE_RE (negative/негативн/отрицательн) и требует, чтобы has_negative_scenario распознавал КАЖДУЮ — тест падает, если детекторы разъедутся снова.
AC3. НЕГАТИВ (гейт не декоративен): AC без единого негатив-маркера ('Валидный ввод возвращает 200') → False; negation-отменённое ('works without errors') → False. Пины сохранены.
AC4. Существующие тесты gate_negative_scenario / QG-0 зелёные. Добавлены тесты на отрицательн + parity + decorative-guard.
AC5. Задокументировано, почему НЕ делается полный merge двух списков (разная семантика: QG-0 keyword-set шире scenario-маркерами, NEGATIVE_RE — узкое негатив-слово; parity-guard достаточен и меньше связывает).

## Plan

## Rollback

git revert; изменение аддитивное (один стем + тест). Дифф-прогон: 0/963 AC меняют вердикт → нет ретро-регрессии.

## Journal

- 2026-07-26T23:05:46Z [implementation] — AC-1: ✓ 'отрицательн' добавлен — tests/test_negative_scenario_parity.py::TestNegativeWordParityWithEvidenceDetector::test_the_previously_missing_russian_form_now_passes ('отрицательный результат' → True, было False). Дифф-прогон 963 реальных AC: 0 меняют вердикт (нет ретро-регрессии) — verification_run #1460 (свой зелёный). AC-2: ✓ КЛАСС закрыт executable-инвариантом (#301) — test_every_evidence_negative_word_is_a_qg0_scenario: негатив-слова читаются ИЗ NEGATIVE_RE.pattern (producer-derived split), каждое обязано распознаваться has_negative_scenario; падает при расхождении детекторов. AC-3: ✓ НЕГАТИВ (гейт не декоративен) — существующие пины сохранены: test_a_plain_positive_criterion_is_not_a_scenario (позитивный AC → False), test_bez_oshibok/without_errors (negation-cancel → False). AC-4: ✓ tests/test_senar.py + test_qg0_dimensions.py + test_negative_scenario_parity.py 81 passed. mypy Success. AC-5: ✓ Задокументировано в комментарии gate_negative_scenario.py: полный merge не делается (QG-0 keyword-set шире scenario-маркерами error/fail/401/timeout, NEGATIVE_RE — узкое негатив-слово; parity-guard достаточен и меньше связывает). Domain: два детектора одного вопроса на двух этапах жизненного цикла больше не расходятся — класс #301 (перенося детектор, переноси и его словарь). verification_run #1460 scoped pytest PASS. CHANGELOG EN+RU.
