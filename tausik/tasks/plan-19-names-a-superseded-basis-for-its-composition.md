---
slug: plan-19-names-a-superseded-basis-for-its-composition
title: "TAUSIK-plan-1.9.md называет основанием состава решение #337 и «22 задачи», отменённые #360–#363"
status: done
epic: release-19-renar-conformance
story: release19-proof-integrity
complexity: simple
role: tech-writer
stack: python
tier: light
call_budget: 20
defect_of: null
scope: "TAUSIK-plan-1.9.md, tests/test_release_roadmap.py (или новый tests/test_plan_19_names_the_composition_in_force.py)"
scope_exclude: "ROADMAP.md не редактируется руками; решения не переписываются."
relevant_files:
  - TAUSIK-plan-1.9.md
  - "tests/test_plan_19_names_the_composition_in_force.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-09-13T11:49:05Z"
resolution: null
resolution_reason: null
tracker_refs: []
started_model_id: claude-opus-5
started_model_version: null
done_model_id: claude-opus-5
done_model_version: null
model_mismatch: 0
no_file_changes_declared: 0
token_budget: null
cost_budget_usd: null
---

## Goal

ЗАМЕР, смена #251: TAUSIK-plan-1.9.md (ТЗ на выпуск) в шапке: «Основание состава: решение #337»; §3: «Состав живёт в решении #337 … 22 задачи в счёте, 5 на удержании владельца» и таблица групп 7/5/7/3; §7: «источник состава — решение #337». Решение #360 (2026-09-10) прямо «supersedes decision #337», #361 расширило состав, #362 зафиксировало карту релизов, #363 подтвердило. Документ сам в преамбуле объявляет: «Документ, описывающий несуществующий состав, — это ровно тот дефект „сказанное шире сделанного“, написанный про себя». Никакой тест его не сверяет с журналом решений. Починка минимальная и честная: датированная сноска в шапке и в §3/§7, называющая действующие решения (#360, #361, #362, #363 и пересказ состава из задачи roadmap-reads-an-additive-decision-as-the-whole-composition) и ROADMAP.md как порождённый источник счётчиков; §3 помечен как состав на 07.09, сохранённый историей, а не как действующий. Тест: номер решения, который ROADMAP.md называет составом в силе, встречается в TAUSIK-plan-1.9.md — чтобы следующий пересказ состава не оставил ТЗ с прежним номером. Прошлый текст не переписывается (это датированная запись).

## Acceptance Criteria

AC-1: TAUSIK-plan-1.9.md в шапке называет действующие решения о составе (#360–#369 и решение-пересказ) и ROADMAP.md как источник счётчиков; §3 и §7 помечены датированной сноской «состав по #337 отменён». AC-2: НЕГАТИВ: тест: номер решения, из которого ROADMAP.md берёт состав в силе («Состав — из … решения … #N»), присутствует в TAUSIK-plan-1.9.md; мутация — заменить номер в плане — даёт ошибку теста. AC-3: числа плана, не подтверждённые сегодняшним замером, не переписаны под видом актуальных: §3 явно назван историческим. AC-4: signed verify.

## Plan

## Rollback

git revert.

## Journal

- 2026-09-13T11:48:47Z [implementation] — Сделано: датированная сноска в шапке (#337 отменено; цепочка #360→#369; действующий — #369; ROADMAP.md — источник счётчиков; §3/§7 — историческая запись), пометка в §3, правка §7. Тест tests/test_plan_19_names_the_composition_in_force.py: номер из ROADMAP.md («Состав — из последнего решения … #N») равен номеру в сноске плана; мутация «#337 в сноске» → 1 failed, возврат → 3 passed. Прошлый текст §3 (22 задачи, группы) не переписан — датированная запись.
- 2026-09-13T11:49:02Z [implementation] — AC-1 ✓ TAUSIK-plan-1.9.md шапка: сноска от 13.09 называет #360–#369, действующее #369 и ROADMAP.md; §3 помечен «историческая запись», §7 называет объявляющее решение. AC-2 ✓ (НЕГАТИВ) tests/test_plan_19_names_the_composition_in_force.py::test_the_plan_names_the_decision_the_map_is_built_from (номер из ROADMAP.md = номер в сноске); ::test_a_stale_number_in_the_plan_is_caught; мутация «#337 в сноске» → 1 failed, возврат → 3 passed (журнал). AC-3 ✓ числа §3 не переписаны, раздел назван историческим (::test_the_plan_marks_its_september_7_composition_as_history). AC-4 ✓ verify #2583 подписан. Domain: читатель ТЗ на выпуск с первого абзаца узнаёт, что состав от 7 сентября отменён и где живёт действующий, а не принимает #337 и «22 задачи» за правду.
