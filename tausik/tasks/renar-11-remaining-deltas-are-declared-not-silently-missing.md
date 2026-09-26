---
slug: renar-11-remaining-deltas-are-declared-not-silently-missing
title: "Остальные дельты RENAR 1.1 (комплект описания и set-version, MW, реестр экранов, automation.status, глава 15, AR primary) — сделаны или декларированы как неприменимые с предпосылкой и храповиком"
status: done
epic: release-110-deferred-from-19
story: release110-renar-11-first-party-and-spec-uc
complexity: medium
role: backend
stack: python
tier: null
call_budget: null
defect_of: null
scope: null
scope_exclude: null
relevant_files:
  - "scripts/renar_v11_deltas.py"
  - "scripts/renar_conformance.py"
  - RENAR-CONFORMANCE.yaml
  - "docs/en/renar-11-deltas.md"
  - "docs/ru/renar-11-deltas.md"
  - "tests/test_renar_v11_deltas.py"
scope_paths:
  - "scripts/renar_*.py"
  - "tests/*.py"
  - "docs/ru/*.md"
  - "docs/en/*.md"
  - "docs/README.md"
  - RENAR-CONFORMANCE.yaml
  - "CHANGELOG*.md"
scope_tools: []
depends_on:
  - spec-uc-is-the-twelfth-spec-type
completed_at: "2026-09-23T19:10:26Z"
resolution: null
resolution_reason: null
---

## Goal

guide/12 RENAR 1.1 перечисляет 20 правок; ломающие — комплект описания (BR/SR/SPEC/TC без status/version, set-version N.M, линейная история, QG-0/1/2 по объектам комплекта, манифест set-version) и automation.status из двух значений. У TAUSIK SPEC — «typed, versioned» с собственным статусом, TC-сущности нет, экранов нет, MW нет. Переделка модели версий — по объёму и природе кандидат в 2.0, а не в 1.10; но §13.7.3 требует переоценки заявления немедленно, и молчание о невнедрённой дельте — то же, что ложное «внедрено». Цель: каждая дельта либо внедрена (тривиальные: AR фиксирует primary-модель §4.10.1, ai-provenance по канону), либо декларирована под normative-inapplicability с предпосылкой, читаемой из схемы, и храповиком-тестом — по образцу §13.3.8 (решение #364); set-version — с явным указателем на 2.0.

## Acceptance Criteria

1. Таблица дельт guide/12 (20 строк) в docs/ru+en/renar-11-deltas.md со статусом каждой: внедрено / неприменимо (предпосылка) / отложено (решение #382, #377) / действий не требуется; число строк СЧИТАНО из guide/12 тестом по корпусу.
2. Строка 16 (AR primary, ai-provenance): AR-класса на носителе нет — декларирована неприменимой с предпосылкой, которую читает renar_clause_reactive_adapt.collect_state; появление AR-класса ломает храповик.
3. RENAR-CONFORMANCE.yaml несёт блок renar-11-deltas: неприменимые с предпосылкой и отложенные с решением; НЕГАТИВНЫЙ: строка со статусом implemented без разрешимого механизма module:function — красный тест.
4. Храповик: на живой БД каждая предпосылка неприменимости пуста; тест ломается, когда появляется носитель (MW, uses[], screens/SPEC-UI, AR-класс, уровень RENAR-2+).
5. CHANGELOG EN+RU.

## Plan

## Rollback

git revert; YAML регенерируется.

## Journal

- 2026-09-23T19:07:04Z [implementation] — Сделано: scripts/renar_v11_deltas.py — реестр 20 строк guide/12 (4 implemented, 5 inapplicable, 10 deferred, 1 no-action), validate(), функции предпосылок, section() для манифеста; блок renar-11-deltas в RENAR-CONFORMANCE.yaml (регенерирован через tausik renar conformance --write); docs/en|ru/renar-11-deltas.md + индекс docs/README.md; решение #382 (модель комплекта в 2.0, ждёт владельца) и задача 2.0 renar-11-description-set-model. Попутно найден и исправлен дефект: манифест нёс senar-version 1.3 из своей константы — теперь DECLARED_SENAR_VERSION. AC verified: 1. ✓ test_the_registry_has_exactly_the_rows_of_the_guide (строки читаются из живого корпуса), test_the_page_lists_every_row_with_its_status 2. ✓ в иной форме: строка 16 неприменима — AR-класса на носителе нет, предпосылку читает renar_clause_reactive_adapt.collect_state (renar_v11_deltas.ar_carriers); AC-2 исходной редакции (AR несёт primary.model) невыполним без AR-класса, критерий переписан до старта работы 3. ✓ test_the_committed_manifest_carries_the_block; НЕГАТИВНЫЙ test_implemented_without_a_mechanism_is_refused, test_inapplicable_without_a_premise_and_deferred_without_a_decision_are_refused 4. ✓ test_each_inapplicability_premise_holds_on_the_fresh_schema, test_a_carrier_appearing_breaks_its_premise 5. ✓ CHANGELOG EN+RU. 15 тестов зелёные, 94 теста RENAR/SENAR зелёные.
