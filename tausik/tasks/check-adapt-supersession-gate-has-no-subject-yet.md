---
slug: check-adapt-supersession-gate-has-no-subject-yet
title: "Гейт check-adapt-supersession не существует: висячая ссылка на дезавуированный ADAPT не ловится ничем"
status: planning
epic: release-19-renar-conformance
story: renar-debt-implemented-wrong
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
depends_on:
  - our-only-spec-is-derived-without-either-allowed-source-field
completed_at: null
---

## Goal

ВЫНЕСЕНО ИЗ adapt-status-enum-diverged-from-the-standards-closed-list В СМЕНЕ #210. Не пополнение объёма, а РАЗДЕЛЕНИЕ уже входившей в него работы: исходная задача несла четыре пункта одного вердикта с пометкой «не разрезать», три из них закрыты миграцией v50, четвёртый отложен ЗАМЕРОМ.

ЧЕГО НЕТ. Точки контроля adapt-supersession (§10.11.1 стр.485) и обещанного самим ADR-007 гейта check-adapt-supersession. Висячая ссылка source.adapt на дезавуированный (superseded) ADAPT сегодня не ловится ничем.

ПОЧЕМУ НЕ СДЕЛАНО ВМЕСТЕ С v50, И ЭТО ЗАМЕР, А НЕ УДОБСТВО. Ссылка, которую гейт обязан ловить, живёт в поле source.adapt у SPEC. Замер renar_clause_reactive_adapt.collect_state на живой БД в смене #210 дал spec_provenance_columns=() — колонок провенанса у specs НЕТ НИ ОДНОЙ (из трёх допустимых: source_adapt, source_tz_section, source_adversarial_review_ref). Гейт, которому нечего проверять, есть вырожденный контроль по ADR-021 — ровно тот дефект, который чинила исходная задача. Построить его сейчас значило бы совершить на этаж ниже ту же ошибку.

ЧТО ЗАКРЫТО И НА ЧТО МОЖНО ОПЕРЕТЬСЯ. Субстрат готов: adapts.status несёт закрытый перечень §7.8.1, дезавуирование без основания отклоняется на низшем примитиве (backend_crud_adapts.adapt_set_status), supersession_rationale хранится. То есть «дезавуирование наполовину» уже устранено; недостаёт ИМЕННО ловли висячих ссылок НА дезавуированный ADAPT.

ЗАВИСИМОСТЬ. Появление провенанса у SPEC. Смежная задача our-only-spec-is-derived-without-either-allowed-source-field идёт ВТОРЫМ путём по решению владельца #307 (объявить неприменимость нормы явно, ТЗ как артефакта у нас нет) — если провенанс так и не заводится как поле, эта задача обязана быть переоценена: возможно, её честный исход — тоже явно объявленная неприменимость, а не гейт.

## Acceptance Criteria

## Plan

## Rollback

## Journal
