---
slug: mandatory-clause-13-3-3-is-checked-by-counting-artifacts
title: "Обязательное положение §13.3.3 проверяется у нас счётом «ADAPT больше нуля» — измеритель не способен покраснеть ни на одном нарушении"
status: planning
epic: null
story: null
complexity: complex
role: architect
stack: null
tier: substantial
call_budget: 90
defect_of: six-more-accepted-adrs-have-no-assessment-record
scope: null
scope_exclude: null
relevant_files: []
scope_paths: []
scope_tools: []
depends_on: []
completed_at: null
---

## Goal

НАЙДЕНО В #198 ПРИ ВЫНЕСЕНИИ ВЕРДИКТА ПО ADR-009. Это долг практики, вскрытый вердиктом, и он НЕ поглощается формулировкой вердикта (AC4 материнской задачи).

scripts/renar_conformance.py:126 подтверждает обязательное положение §13.3.3 так: `"adapt_per_tz": adapts > 0,  # data: needs ≥1 ADAPT in the substrate`.

ЧТО ПОЛОЖЕНИЕ ТРЕБУЕТ НА САМОМ ДЕЛЕ (цитаты сверены машиной в файле standard/13-conformance.md):
  стр.73 — «Каждое ТЗ обязано пройти состязательный обзор (§7.10.2); его исход обязан быть выпущен как AR — запись состязательного обзора в статусе `issued`»;
  стр.77 — при вердикте findings-present «ADAPT обязателен в статусе `approved` с подписью Архитектора», каждая находка несёт decided-in на пункт ПОДПИСАННОГО ACTZ, AR несёт непустой produces-adapt[];
  стр.80 — «Создание BR / SR / SPEC из ТЗ без зафиксированного вердикта — нарушение стандарта»;
  reference/normative-index.yaml стр.36 — MC-13.3.3, modality MUST, produces: [ADAPT, AR, ACTZ], gate QG-ADAPT-approve. Версия индекса 1.0 — та же, к которой заявляемся мы.

ИЗМЕРИТЕЛЬ ВЫРОЖДЕН ПО ОПРЕДЕЛЕНИЮ ADR-021: счёт «больше нуля» не краснеет НИ НА ОДНОМ из этих нарушений. Проверка живая, а не гипотетическая: наш единственный ADAPT стоит в status: draft с signatures: [] и НЕПУСТЫМ разделом Backward findings, AR у нас ноль (каталога renar/ar/ нет, грep по scripts/ на adversarial-review-ref и AR-NNN даёт ноль совпадений), ACTZ нет как класса. То есть положение нарушено сразу по трём основаниям, а измеритель показывает зелёное.

ЦЕНА, И ОНА НЕ ВНУТРЕННЯЯ. Из adapt-per-tz: true выводится pre-adoption: false, а из него — весь наш заявленный уровень RENAR-1. Этот самый факт отправлен в корпус стандарта тикетом renar#47 (задача adr-020-states-a-stale-fact-about-our-conformance-claim, та же смена). Если измеритель вырожден, отправленный наружу факт не доказан, и тикет требует поправки. Работа по этой задаче обязана закончиться решением о судьбе #47, а не только починкой кода.

ЧТО ДЕЛАЕТСЯ: измеритель §13.3.3 переписывается так, чтобы КРАСНЕЛ на каждом из перечисленных нарушений, и к нему заводится red-proof в tausik/gates.json по правилу решения #288. Отдельный вопрос, требующий ответа ДО кода: считать ли, что предмет §13.3.3 у нас вообще существует — tz_ref нашего ADAPT указывает на decisions#109, то есть на ЗАПИСЬ, а не на ТЗ-артефакт. Вакуумная истина здесь допустима, но обязана быть ОБЪЯВЛЕНА, как это сделано для tc-pos-neg-pairing, а не получена счётом.

## Acceptance Criteria

## Plan

## Rollback

## Journal
