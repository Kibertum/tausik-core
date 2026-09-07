---
slug: senar-version-claimed-in-three-places-disagrees
title: "Продукт заявляет три разные версии SENAR одновременно: 1.3 в CLAUDE.md, 1.5 в матрице соответствия, без версии в README"
status: planning
epic: release-19-renar-conformance
story: evidence-primitives
complexity: medium
role: architect
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

ЗАМЕР СНЯТ В СМЕНЕ #223 ПРИ ПОДГОТОВКЕ senar-14-conformance-reassessment-and-self-check.

ПРОДУКТ ГОВОРИТ О СЕБЕ ТРИ РАЗНЫЕ ВЕЩИ ОДНОВРЕМЕННО:
  CLAUDE.md:7 — «Реализует SENAR v1.3»;
  docs/ru/senar-compliance-matrix.md и docs/en/senar-compliance-matrix.md — заголовок «SENAR v1.5 Core — Матрица соответствия», дата 2026-06-13, фреймворк TAUSIK v1.7.0;
  README.md:183 — версия не названа вовсе («the reference implementation of SENAR»).

ПОЧЕМУ ЭТО НЕ КОСМЕТИКА. Заявление о соответствии — публичное утверждение, а §13.6 стандарта делает переоценку ОБЯЗАННОСТЬЮ при смене мажорной версии. Пока три источника называют три разные версии, невозможно даже сказать, ЧТО именно переоценивать: заявление 1.3, заявление 1.5 или отсутствие заявления. Любая работа по переоценке начинается с этой развилки, поэтому она вынесена отдельно и раньше.

ЧТО НЕ ВХОДИТ: сама переоценка по §13.7 (это задача senar-14-conformance-reassessment-and-self-check, у неё свой блокер — нормативного текста §13.6-13.7 в дереве нет). Здесь только привести три места к ОДНОМУ заявлению и завести охрану, чтобы они снова не разъехались.

РЕШЕНИЕ ВЛАДЕЛЬЦА: какую версию заявляем. Агент может свести источники к одному значению, но не может выбрать, какое именно публичное утверждение делает продукт.

НЕГАТИВНЫЙ СЦЕНАРИЙ: охрана, которая молчит, когда версия названа в новом четвёртом месте, бесполезна. Тест обязан краснеть, когда любой из источников расходится с остальными, и называть разошедшийся файл.

## Acceptance Criteria

## Plan

## Rollback

## Journal
