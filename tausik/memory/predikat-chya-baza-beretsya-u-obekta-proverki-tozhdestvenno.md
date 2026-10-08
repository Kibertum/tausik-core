---
slug: predikat-chya-baza-beretsya-u-obekta-proverki-tozhdestvenno
title: "Предикат, чья база берётся у объекта проверки, тождественно ложен"
type: gotcha
tags:
  - doctor
  - senar
  - trust-tiers
task: doctor-says-nothing-weakens-enforcement-while-the-user-tier-does
edges: []
---

config_trust сравнивал кандидата с БАЗОЙ, а базой служили сами доверенные тиры. Для проектного слоя это верно, а для тира-субъекта предикат не может сработать никогда: тир не слабее самого себя по построению. Поэтому ослабление сверху не имело НИ ОДНОГО машинного признака и нашлось только чтением ~/.tausik/config.json глазами (сессия #193). Признак дефекта в коде: is_weaker(candidate, baseline), где baseline вычисляется из того же слоя, откуда пришёл candidate. Лечение: базу берут у стороны, которая объектом проверки НЕ является — framework_default(guard, path), а не _baseline_for(..., trusted). Тот же вопрос задавай любому контролю: 'по чему он меряет и входит ли предмет в эту базу'.
