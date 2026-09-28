---
slug: checklist-warning-contradicts-the-evidence-it-reads
title: "Предупреждение о чек-листе утверждает, что критерии не называют тестов, когда они их называют"
status: done
epic: release-110-deferred-from-19
story: release110-verification-is-cheap
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/service_ac_evidence.py"
  - "tests/test_checklist_reads_ac_prefixed_items.py"
scope_paths:
  - "scripts/ac_evidence_detectors.py"
  - "scripts/service_ac_evidence.py"
  - "scripts/gate_ac_check.py"
  - "tests/*.py"
  - "CHANGELOG*.md"
scope_tools: []
depends_on: []
completed_at: "2026-09-23T22:22:36Z"
resolution: null
resolution_reason: null
tracker_refs:
  - "github#20"
started_model_id: null
started_model_version: null
done_model_id: null
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
---

## Goal

НАБЛЮДЕНИЕ, смена #241, НЕ ДОВЕДЁННОЕ ДО ДИАГНОЗА - и записано именно так, чтобы следующий не принял догадку за замер. При закрытии both-trackers-carry-fixed-issues-nobody-closed напечатано: 'Verification checklist (standard, 10 items) - no acceptance criterion names a test, a manual run, a review or a green verification_run.' Между тем в журнале задачи лежат пять строк вида 'AC-2: ✓ tests/test_tracker_ref.py::TestГолыйНомерОтвергнут::test_номер_без_трекера_отказ', и TEST_REF_RE их НАХОДИТ - проверено прямым вызовом на всех четырёх формах, включая кириллические имена классов.

ДВЕ ВОЗМОЖНОСТИ, и их надо РАЗЛИЧИТЬ ЗАМЕРОМ, а не выбрать:
1. Предупреждение говорит о ДРУГОМ артефакте - о десятипунктовом чек-листе проверки, а не о доказательствах критериев, - и тогда дефект в ФОРМУЛИРОВКЕ: она утверждает 'no acceptance criterion names a test' там, где критерии их называют, и читатель идёт чинить несуществующее.
2. Предупреждение говорит именно о доказательствах, и тогда есть настоящий разрыв между TEST_REF_RE и тем, что читает чек-лист.

ПОЧЕМУ ЭТО НЕ КОСМЕТИКА В ЛЮБОМ ИЗ ДВУХ СЛУЧАЕВ. Предупреждение, срабатывающее на верно оформленном доказательстве, обучает пролистывать себя. Это тот же механизм, из-за которого в этом релизе пришлось объявлять остаток по цитатам закрытий: находка, которая повторяется и с которой ничего нельзя сделать, обесценивает всю свою категорию.

## Acceptance Criteria

AC-1 ЗАМЕР ПЕРВЫМ: названо, какой именно артефакт читает предупреждение и почему оно сработало на этой задаче — цитатой кода, а не рассуждением. AC-2 Если дефект в формулировке: текст говорит, ЧЕГО не хватает, не отрицая того, что есть. AC-3 Если дефект в разрыве детекторов: доказательство, распознанное TEST_REF_RE, распознаётся и чек-листом. AC-4 НЕГАТИВ: задача, у которой доказательств действительно нет, ПО-ПРЕЖНЕМУ получает предупреждение — правка не смеет стать глушилкой.

## Plan

## Rollback

Правка текста предупреждения либо детектора; откат — git revert. Поведение гейтов не меняется: предупреждение не блокирует.

## Journal

- 2026-09-23T22:21:19Z [implementation] — AC-1 замер: предупреждение печатает gate_ac_check.check_verification_checklist по checklist_missing -> _evidence_strength -> service_ac_evidence.build_report. На AC задачи #241 ('AC-1 Связь… AC-2 Ссылка…', без точки после номера) parse_ac_text возвращал ОДИН пункт: AC_ITEM_BOUNDARY_RE требует [.):] после номера. Доказательство 'AC-2: ✓ tests/…' ссылалось на пункт 2, которого нет, with_activity=0 -> заметка. Значит, вариант 2: разрыв детекторов, а не формулировка. Проверено воспроизведением: с AC построчно те же ссылки дают (2,2,3).
- 2026-09-23T22:21:19Z [implementation] — AC-1: ✓ tests/test_checklist_reads_ac_prefixed_items.py::test_inline_ac_prefixed_items_are_three_items
- 2026-09-23T22:21:19Z [implementation] — AC-3: ✓ tests/test_checklist_reads_ac_prefixed_items.py::test_the_evidence_is_bound_and_the_warning_stays_quiet
- 2026-09-23T22:21:20Z [implementation] — AC-2: не применимо — дефект не в формулировке. NO-DEAD-END: причина найдена прямым воспроизведением
- 2026-09-23T22:21:20Z [implementation] — AC-4: ✓ tests/test_checklist_reads_ac_prefixed_items.py::test_a_task_with_no_evidence_is_still_warned
- 2026-09-23T22:21:20Z [implementation] — AC-4: ✓ tests/test_checklist_reads_ac_prefixed_items.py::test_prose_numbers_without_the_prefix_do_not_split
