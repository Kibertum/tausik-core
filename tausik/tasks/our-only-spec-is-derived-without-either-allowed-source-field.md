---
slug: our-only-spec-is-derived-without-either-allowed-source-field
title: "Три SPEC выведены без обоих допустимых источников: ни source.tz-section, ни source.adapt — дословный негативный сценарий §13.3.3"
status: planning
epic: release-19-renar-conformance
story: renar-debt-implemented-wrong
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 55
defect_of: null
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on:
  - mandatory-clause-13-3-3-is-checked-by-counting-artifacts
completed_at: null
---

## Goal

НАЙДЕНО В #198 ПРИ ВЫНЕСЕНИИ ВЕРДИКТА ПО ADR-006. Долг практики, вскрытый вердиктом, уходит отдельной задачей и не поглощается формулировкой вердикта.

НОРМА. ADR-006 таблица источников, стр.76: «| SPEC | conditional | mandatory всегда (для traceability) |» — то есть `source.tz-section` обязателен для SPEC ВСЕГДА, при любом исходе состязательного обзора. §13.3.3 называет обратное негативным сценарием дословно, стр.90: «...но BR/SR/SPEC производятся из ТЗ без `source.tz-section` и без `source.adapt` — нарушение обязательного происхождения».

МЫ. renar/specs/renar-adoption.md несёт `content_ref: decisions#109` (стр.3) и не несёт НИ ОДНОГО поля происхождения: ни `tz-section`, ни `adversarial-review-ref`, ни `source.adapt`. Обе первые строки проверены на ОТСУТСТВИЕ отдельной машинной ветвью, ветвь промутирована заведомо присутствующей строкой и покраснела. Связь с нашим ADAPT идёт в ОБРАТНУЮ сторону — из ADAPT в SPEC через links, — то есть провенанс не выражен там, где его ищет норма и где его искал бы аудитор.

ПОЧЕМУ ЭТО НЕ ОДИНОКАЯ ОПЕЧАТКА. `content_ref: decisions#109` указывает на ЗАПИСЬ в нашей БД, а не на раздел ТЗ. Тот же дефект пойман с другой стороны в #197: новый контроль полноты тела SPEC пометил renar-adoption как UNCHECKED именно потому, что предмет его тела не назван, а content_ref ведёт в decisions#109. Два независимых контроля, построенных по разным основаниям, указали на одно место — признак настоящего дефекта, а не придирки.

ЧТО ДЕЛАЕТСЯ. Ввести поля происхождения в модель SPEC и заполнить их для существующего артефакта, либо — если решено, что ТЗ у нас не существует как артефакта — объявить это ЯВНО и показать, что норма к нам неприменима, вместо молчаливого пропуска поля. Второй путь требует ответа на вопрос, который сегодня без ответа: считается ли decisions#109 нашим ТЗ. Ответ на него общий с mandatory-clause-13-3-3-is-checked-by-counting-artifacts, поэтому задачи связываются, а не сливаются: там измеритель, здесь артефакт.

ЗАВИСИМОСТЬ ОТ РЕШЕНИЯ О ЗАЯВКЕ: если по our-conformance-claim-rests-on-a-mode-the-standard-removed заявка о соответствии снимается, эта задача не исчезает — провенанс SPEC полезен нам самим, — но её срочность падает с «нарушаем норму» до «теряем прослеживаемость».

## Acceptance Criteria

## Plan

## Rollback

## Journal

- 2026-09-04T11:02:12Z [planning] — ПРЕМИСА ПОПРАВЛЕНА ЗАМЕРОМ, ЗАДАЧА НЕ ВЗЯТА. В #198 заголовок говорил «единственный SPEC». Замер #209: renar/specs/ содержит ТРИ артефакта — renar-adoption (content_ref: decisions#109), sec-config-trust-tiers (content_ref: docs/ru/config-trust-tiers.md), team-state-in-git-format (content_ref: docs/ru/team-state-in-git.md). Полей происхождения нет НИ У ОДНОГО: ни source.tz-section, ни source.adapt, ни adversarial-review-ref. Заголовок исправлен на «Три SPEC». РЕШЕНИЕ ВЛАДЕЛЬЦА ПОЛУЧЕНО (решение #307): decisions#109 НЕ считается нашим ТЗ, ТЗ как артефакта у нас нет, и это объявляется ЯВНО. Значит задача идёт по ВТОРОМУ пути собственного описания: показать неприменимость нормы записью со ссылкой на renar-first-tz-adapt, а не заполнять tz-section. Объявление обязано покрыть ВСЕ ТРИ артефакта. Миграция v50 скорее не нужна — решать инвентарём при взятии.
