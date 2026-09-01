---
slug: four-tests-fail-in-a-bare-checkout
title: "Четыре теста падают в чистой выгрузке на коммите, где рабочее дерево зелёное"
status: planning
epic: release-19-renar-conformance
story: evidence-primitives
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

НАЙДЕНО ЗАМЕРОМ В #203 ПРИ РАБОТЕ НАД db-gated-ratchets-never-run-in-ci. Класс дефекта ДРУГОЙ, поэтому по решению #296 отдельной задачей: там контроли ТИХО ПРОПУСКАЛИСЬ, здесь они ПАДАЮТ.

ЗАМЕР. В git worktree на коммите e397093, где рабочее дерево даёт 7759 passed / 0 failed, полная лента даёт 7 failed. Выгрузка подготовлена ровно как в CI: checkout плюс `python bootstrap/bootstrap.py --no-detect --ide all`. ЧЕТЫРЕ падения воспроизводятся ИЗОЛИРОВАННО при отсутствующей базе, то есть это не грязь от базы, которую лента создаёт по ходу:
— tests/test_spec_completeness.py::test_the_live_repository_reports_exactly_the_gap_it_has
— tests/test_gate_degeneracy.py::test_an_entry_with_no_test_node_is_not_a_proof
— tests/test_gate_degeneracy.py::test_every_blocking_gate_in_force_has_a_resolving_red_proof
— tests/test_doctor_trust_tier_weakening.py::test_doctor_calls_it_a_warning_and_not_a_failure
Последний виден полностью: тест ждёт в выводе doctor слово «warning(s)», а получает «FAIL 1 FAIL, 3 WARN» — в голой выгрузке doctor находит настоящий FAIL, которого в рабочей копии нет.

ПОЧЕМУ ЭТО ВАЖНО. Названия говорят сами за себя: три из четырёх — про доказательность гейтов и полноту SPEC, то есть ровно та машинерия, на которую опирается релиз 1.9. Если бы CI выполнялся на этой ветке, он был бы КРАСНЫМ. Он не выполняется (см. задачу ci-does-not-run-on-the-release-branch), поэтому никто не узнал.

ЧТО НУЖНО РЕШИТЬ ПО КАЖДОМУ, А НЕ СКОПОМ. Для каждого из четырёх ответить отдельно: (1) это тест, чей предмет есть рабочая копия, и он обязан честно спать в выгрузке — тогда завести его в реестр ALLOWED_DORMANT (tests/test_no_silent_db_gated_skips.py) и цитировать conftest.DORMANT_WITHOUT_LIVE_DB; либо (2) это НАСТОЯЩИЙ дефект, который выгрузка обнажила, — тогда чинить предмет, а не тест. Соблазн пометить все четыре как «локальные» велик и, вероятно, неверен как минимум для одного: doctor, находящий FAIL в свежем клоне, есть утверждение о продукте, а не о машине.

НАЧИНАТЬ С ЗАМЕРА: воспроизвести в git worktree (память #501) и предъявить для каждого, ЧТО именно отсутствует и почему это меняет вердикт.

## Acceptance Criteria

## Plan

## Rollback

## Journal
