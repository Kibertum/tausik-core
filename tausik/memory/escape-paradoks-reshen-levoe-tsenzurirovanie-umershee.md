---
slug: escape-paradoks-reshen-levoe-tsenzurirovanie-umershee
title: "Escape-парадокс решён: левое цензурирование + умершее лечение, а не вред verify"
type: context
tags:
  - "escape-rate,verified,defect-of,simpson,left-censoring"
task: investigate-the-verified-vs-unverified-escape
edges: []
---

investigate-the-verified-vs-unverified-escape (закрывает гипотезу #267; доказательство — tests/test_defect_escape.py::TestStratifiedVerification и журнал задачи): агрегат verified 9.9% (138/1400) против unverified 1.5% (6/395), Fisher p=8.8e-10 — НЕ малая выборка и НЕ «verify вредит». Причины: (1) практика defect_of началась 2026-04, на доапрельские закрытия не указывает ни один дефект, а 230/395 unverified-закрытий — март (структурно не могут сбежать); (2) с июля QG-2 делает verify обязательным — unverified-рука не назначается (15 закрытий за 3 месяца против 856 verified). Разрез внутри страт сложности разрыв НЕ снимает (complex 18.1%/0.0%, medium 12.4%/1.1%, simple 5.8%/2.4%) — страты наследуют смешение эпох. Era-clean: unverified после 2026-04-15 — 6/98=6.1% против verified июль+ 117/856=13.7%. risk_score: AUC 0.5377 агрегат / 0.5411 verified-only — монета; не использовать для маршрутизации (решение #424). Окно данных: done n=1795, 2026-03-14..2026-10-06; база #126 от 2026-07-20: 5.1%/1.3% при n=625/380.
