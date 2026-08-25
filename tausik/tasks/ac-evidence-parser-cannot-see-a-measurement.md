---
slug: ac-evidence-parser-cannot-see-a-measurement
title: "Разборщик AC-evidence не умеет читать ИЗМЕРЕНИЕ: доказательство прогоном считается отсутствующим, а галочка — присутствующим"
status: done
epic: null
story: null
complexity: medium
role: architect
stack: python
tier: substantial
call_budget: 70
defect_of: null
scope: "scripts/ac_evidence_detectors.py (VERIFICATION_RUN_RE + PYTEST_SUMMARY_RE), scripts/service_ac_evidence.py (EvidenceLine.is_measurement/measurement_run_id + evidence_type), scripts/gate_ac_check.py (measurement как activity, fact-check по verified_run_ids), scripts/service_gates.py (собрать green_run_ids из be), tests/"
scope_exclude: "Не менять _test_ref_exists / test_ref семантику; verification_runs схему не трогать; hard-block по-прежнему требует резолвимый тест ИЛИ верифицированное измерение (не ослаблять до формы)"
relevant_files:
  - "scripts/ac_evidence_detectors.py"
  - "scripts/service_ac_evidence.py"
  - "scripts/gate_ac_check.py"
  - "scripts/service_gates.py"
  - "scripts/service_task_done.py"
  - "tests/test_ac_measurement_factcheck.py"
  - "tests/test_ac_evidence.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-26T22:59:32Z"
---

## Goal

Найдено при закрытии full-pytest-hangs-while-scoped-pytest-is-green (сессия #135). Закрытие получило NOTE «found 2/5 criteria with explicit evidence (gaps: AC 1, 2, 4)» при том, что именно эти три критерия доказаны САМЫМ сильным способом из имеющихся в проекте — измерением: полный прогон `5778 passed, 23 skipped, 140 deselected in 564.12s`, три независимых замера (faulthandler-молчание, --durations, прогон без таймаута) и сверка цифр evidence сессии #134 с реальным прогоном.

Механика (scripts/service_ac_evidence.py:54-63). AC считается покрытым, если у сопоставленной строки evidence_type != "none", а он бывает только четырёх видов: test_ref (путь tests/...), manual (слово «вручную»/manual), review_ref (слово «ревью»/adversarial), checkmark_only (символ галочки). Измерения в этом списке НЕТ. Следствие ровно то, за которое проект наказывает в других местах: чтобы снять замечание, достаточно ДОПИСАТЬ ГАЛОЧКУ — форма проходит, факт не проверяется. А честная строка «полный pytest 5778 passed за 564 s, verification_run #1285» не проходит, потому что в ней нет ни пути к тесту, ни галочки. Детектор учит агента украшать, а не доказывать (конвенция #297, память #302).

Что делать — предложение, а не приказ. Ввести пятый тип evidence: measurement. И сделать его НЕ ещё одним словарным детектором, а единственным в реестре, который проверяет ФАКТ: строка вида `verification_run #NNNN` сверяется с таблицей verification_runs (существует ли прогон, тот ли task_slug, зелёный ли, не старше ли закрытия), а сводка pytest вида `N passed ... in T s` признаётся измерением по форме числа, а не по слову. Тогда самый сильный вид доказательства становится и самым дешёвым в написании, а галочка перестаёт быть кратчайшим путём.

Проверить заодно: не станет ли measurement новым способом украшать (строка «verification_run #1» с чужим или красным прогоном обязана НЕ засчитываться — это и есть тест на то, что детектор читает факт).

## Acceptance Criteria

AC1. Пятый evidence_type 'measurement': строка `verification_run #NNNN` и pytest-сводка `N passed ... in T s` распознаются парсером (is_measurement=True); measurement_run_id извлекается из `verification_run #NNNN`. report.covered засчитывает measurement по ФОРМЕ (паритет с test_ref).
AC2. ФАКТ-проверка (не словарь): verification_run засчитывается как ACTIVITY (clears checklist_missing / with_activity) ТОЛЬКО если run существует, task_slug совпадает и exit_code==0 (зелёный). Реализовано через verified_run_ids, собранный service_gates из be.verification_runs_for_task(slug).
AC3. НЕГАТИВ (детектор читает факт, не форму): `verification_run #1` с несуществующим / чужим (другой task_slug) / красным (exit_code!=0) прогоном НЕ засчитывается как activity. Тест на каждый из трёх случаев.
AC4. Галочка перестаёт быть кратчайшим путём: задача, доказанная ТОЛЬКО измерением (зелёный verification_run, без test_ref/manual/review/галочки), проходит checklist_missit==False и не получает NOTE «no criterion names a test/manual/review».
AC5. Обратная совместимость + тесты: verified_run_ids=None (legacy/pure) → measurement не засчитывается фактом, старые тесты зелёные. Существующая суита gate_ac_check/ac_evidence зелёная.

## Plan

## Rollback

git revert; изменение аддитивное (новый evidence_type + optional verified_run_ids param, default None → форма как раньше). Обратная совместимость: пустой verified_run_ids → измерение не засчитывается фактом, поведение как до правки.

## Journal

- 2026-07-26T22:58:40Z [implementation] — AC-1: ✓ 5-й тип 'measurement' — tests/test_ac_evidence.py::test_verification_run_is_a_measurement_with_captured_id (run_id=1450), test_pytest_summary_is_a_measurement_by_number_form (run_id=None), test_measurement_counts_toward_covered_by_form (covered по форме, паритет с test_ref). verification_run #1456 (эта задача, зелёный). AC-2: ✓ ФАКТ-проверка — tests/test_ac_measurement_factcheck.py::test_verified_run_clears_activity_gate (green run 1450 → activity=2). _green_verification_run_ids собирает exit_code==0 по slug из be.verification_runs_for_task. AC-3: ✓ НЕГАТИВ (детектор читает факт) — test_unverified_run_does_not_clear_gate (пусто/999/1451 → checklist_missing True) + test_green_run_ids_filter_exit_code_and_slug (red-mine и green-other исключены, только green-mine включён). Три случая: несуществующий/чужой slug/красный. AC-4: ✓ Галочка не кратчайший путь — test_verified_run_clears_activity_gate + test_checklist_note_gone_when_measurement_verified (задача только с зелёным run → NOTE 'no criterion names a test/manual/review' исчезает). ДОГФУД: эта задача цитирует verification_run #1456 (зелёный, свой) как evidence. AC-5: ✓ Обратная совместимость — verified_run_ids=None default → measurement не засчитывается фактом (test_bare_pytest_summary_is_not_activity_without_a_run). Суита gate/task_done/verify/ac_evidence 1303 passed. Parity-тест зелёный (VERIFICATION_RUN_RE/PYTEST_SUMMARY_RE в STRUCTURAL_DETECTORS). mypy 5 файлов Success. verification_run #1456 scoped pytest PASS. Domain: гейт теперь читает сильнейшее доказательство проекта (подписанный зелёный прогон) как факт, а не наказывает за его форму — класс #297/#302 (детектор учит доказывать, не украшать). CHANGELOG EN+RU.
- 2026-07-26T22:59:30Z [implementation] — AC-1: ✓ 5-й тип 'measurement' — test_verification_run_is_a_measurement_with_captured_id (run_id), test_pytest_summary_is_a_measurement_by_number_form, test_measurement_counts_toward_covered_by_form. AC-2: ✓ ФАКТ-проверка verified_run_ids — test_verified_run_clears_activity_gate + _green_verification_run_ids фильтрует exit_code==0/slug. AC-3: ✓ НЕГАТИВ — test_unverified_run_does_not_clear_gate (несуществующий/чужой/красный) + test_green_run_ids_filter_exit_code_and_slug. AC-4: ✓ test_checklist_note_gone_when_measurement_verified; ДОГФУД: verification_run #1458 (свой зелёный) цитируется как evidence. AC-5: ✓ verified_run_ids=None → форма-only (test_bare_pytest_summary_is_not_activity_without_a_run); суита gate/task_done/verify 1303 passed; parity зелёный; filesize 399<400; mypy 5 файлов Success. Domain: сильнейшее доказательство (подписанный зелёный прогон) читается как факт — класс #297/#302. CHANGELOG EN+RU.
