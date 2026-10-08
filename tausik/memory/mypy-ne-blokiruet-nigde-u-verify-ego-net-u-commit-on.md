---
slug: mypy-ne-blokiruet-nigde-u-verify-ego-net-u-commit-on
title: "mypy не блокирует нигде: у verify его нет, у commit он severity=warn"
type: gotcha
tags:
  - commit
  - gates
  - mypy
  - verify
task: null
edges: []
---

На ошибку типов сегодня не блокирует НИ ОДИН триггер: у verify гейта mypy нет вовсе, а у commit он severity=warn. Замерено в #189 мутацией: снятая аннотация даёт [FAIL] mypy ...:147 [var-annotated], и тут же «WARNINGS: Non-blocking issues found» — коммит бы прошёл. Источник значения — scripts/gate_registry.py:114 (default_config severity "warn"); .tausik/config.json включает гейт (enabled: true) и severity не переопределяет. Следствие: фраза «гейт коммита поймал» верна про печать и неверна про остановку — читая вывод gate_runner, различай [FAIL] (block) и [FAIL] (warn). Дополняет память #428 (наборы гейтов verify и commit различаются на пять гейтов).
