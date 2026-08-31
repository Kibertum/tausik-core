---
slug: cli-chitaet-razvernutuyu-kopiyu-v-claude-a-ne-scripts-mer
title: "CLI читает РАЗВЁРНУТУЮ копию в .claude/, а не scripts/ — мерь после bootstrap"
type: gotcha
tags: []
task: pairing-clause-reds-on-the-wrong-duty
edges: []
---

Правка в scripts/renar_measurer_caveats.py не отразилась в манифесте: команда tausik renar conformance --write отработала, а секция оговорок не появилась. Причина не в коде: CLI исполняет развёрнутую копию из .claude/, и она была старой. После bootstrap.py --ide all та же команда дала верный результат. Отсюда правило: любое поведение, наблюдаемое ЧЕРЕЗ CLI или MCP, меряй только ПОСЛЕ bootstrap; иначе замер относится к прошлой версии кода и читается как «правка не работает». Вторая ловушка рядом: renar conformance БЕЗ --write ничего не пишет, только печатает — пустой git diff после неё не есть доказательство, что артефакт не меняется.
