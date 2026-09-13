---
slug: tekst-otkaza-v-dokumentatsii-dlya-agenta-snimaetsya-s
title: "Текст отказа в документации для агента снимается с живого вызова и удерживается тестом по фразе из кода — не пересказывается"
type: convention
tags:
  - agent
  - docs
  - quickstart
  - testing
task: quickstart-tells-a-new-agent-how-to-connect-and-how-to-work
edges: []
---

Смена #257, agent-quickstart. Способ: свежий проект-потребитель в scratchpad (bootstrap --init --ide claude), затем пройти цикл руками и НАМЕРЕННО ошибиться на каждом гейте (task start без AC, без негативного сценария; task done без --ac-verified, без доказательства; Write без активной задачи через развёрнутый task_gate.py; verify без ключа) — вывод копируется в страницу как есть. Тест tests/test_agent_quickstart.py держит каждую цитату двумя утверждениями: фраза есть на странице И фраза есть в исходнике, который её печатает; хосты = SCAFFOLD_IDES, инструменты ∈ TOOLS, команды парсятся build_parser. Почему: агент, выучивший из документации сообщение, которого инструмент не скажет, ищет несуществующий отказ; страница про «как работать» гниёт первой, потому что её никто не запускает. Ловушка: CLI-двойники в тексте `.tausik/tausik <cmd> --flag` — регексп подкоманды не должен ловить флаг ([a-z][a-z-]*).
