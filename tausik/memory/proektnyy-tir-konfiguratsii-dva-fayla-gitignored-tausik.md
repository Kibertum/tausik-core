---
slug: proektnyy-tir-konfiguratsii-dva-fayla-gitignored-tausik
title: "Проектный тир конфигурации — ДВА файла: gitignored .tausik/config.json и закоммиченный tausik/policy.json; «дубль ключа» ищи по обоим"
type: gotcha
tags:
  - config
  - gates
  - policy
  - premise
task: changelog-gate-double-registration-premise-unconfirmed
edges: []
---

Пункт «дубль changelog_gate в .tausik/config.json» кочевал по передачам с #206, а замер #210 по одному файлу нашёл одно вхождение и объявил премису неподтверждённой. Носитель дубля — второй файл того же тира: tausik/policy.json (решение #287, коммит de9e027 перевёз туда changelog_gate, остаток в config.json не убрал). Правило замера: слой конфигурации обходить целиком — .tausik/config.json, tausik/policy.json, ~/.tausik/config.json, реестр gate_registry.py, tausik/gates.json (последний — классификация, не включение). Композиция compose_project_tier: local побеждает на обычных ключах, на охраняемых побеждает строгий, поэтому одинаковые копии безвредны, а лишнюю копию в gitignored файле можно убирать — gates status остаётся [ON] (проверено в #213).
