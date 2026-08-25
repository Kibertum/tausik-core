---
slug: drift-geyt-razlichay-declared-intent-exact-pin-i-derived
title: "Drift-гейт: различай DECLARED intent (exact-pin) и DERIVED measurement (lower-bound)"
type: convention
tags:
  - doc-constants
  - drift
  - gate-design
  - senar
task: doc-constants-drift-is-a-trap-every-task-steps-in
edges: []
---

Константа в doc-constants/drift-проверке бывает двух родов, и проверять их одинаково — баг. DECLARED (version, MCP tool counts, code counts) — задекларированный intent: дрейф = кто-то забыл обновить → exact-pin оправдан. DERIVED (test_count) — измерение, меняется почти от каждой задачи: exact-pin делает нормальную работу «дрейфом» (add test → green close → полный набор красный). DERIVED проверять как НИЖНЮЮ ГРАНИЦУ: рост (recorded ≤ live) не дрейф; красный только на осмысленном — усадка ниже пола ИЛИ doc-overclaim (заявлено больше чем есть). Так проверяемый факт сохраняется в направлении, где он значит регрессию. Решение #182, задача doc-constants-drift-is-a-trap. Ср. класс #305 (знаменатель рядом с вердиктом) и #306 (прокси-метрика вычитает делопроизводство).
