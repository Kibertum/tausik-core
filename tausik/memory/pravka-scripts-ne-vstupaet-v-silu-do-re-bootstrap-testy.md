---
slug: pravka-scripts-ne-vstupaet-v-silu-do-re-bootstrap-testy
title: "Правка scripts/ не вступает в силу до ре-bootstrap: тесты зелёные по источнику, хуки исполняют старую копию"
type: gotcha
tags:
  - bootstrap
  - dogfooding
  - hooks
  - senar
task: bootstrap-drift-not-gated-stale-runtime
edges: []
---

ИСТОЧНИК — scripts/ и harness/. ИСПОЛНЯЮТСЯ сгенерированные bootstrap копии в профилях IDE: .claude/, .cursor/, .kilo/, .opencode/, .qwen/. Набор тестов импортирует из scripts/ (pythonpath=["scripts"] в pyproject.toml), поэтому он зелёный по ИСТОЧНИКУ и ничего не знает о копиях.

СЛЕДСТВИЕ, УПЛАЧЕННОЕ НА СЕБЕ (сессия #121 -> обнаружено аудитом в #122): правка докстринга scripts/risk_l3_trigger.py прошла полный зелёный прогон в обоих режимах, закрылась через task done и ушла в коммит, а .claude/scripts/risk_l3_trigger.py остался старым. То есть исправление было в репозитории и НЕ ДЕЙСТВОВАЛО.

ОПАСНО ИМЕННО ДЛЯ ХУКОВ И ГЕЙТОВ. Если правишь scripts/hooks/*.py или логику гейта — до `python bootstrap/bootstrap.py --update` она не вступит в силу, а прогон будет зелёным. Агент решит, что починил.

ПРИЗНАК И ЛЕЧЕНИЕ: `tausik doctor` печатает «WARN Bootstrap drift: N script(s) differ». Doctor НЕ входит ни в тесты, ни в гейты verify, ни в task done — то есть увидеть это можно только вызвав его руками. Лечение: `python bootstrap/bootstrap.py --update`.

ПРАВИЛО: правил что-то в scripts/ или harness/, что исполняется хуком, MCP или гейтом, — пересобери bootstrap ДО того, как поверишь зелёному прогону.

ГРАНИЦА, чтобы не раздувать: профили в .gitignore, пользователям дрейф не отгружается (свежий клон собирается из источника). Это дефект рабочего цикла, а не поставки. Гейт заводится задачей bootstrap-drift-not-gated-stale-runtime.

Связано: [[nezakommichennyy-dolg-strukturno-blokiruet-qg2]] — оба про то, что состояние среды молча меняет смысл зелёного.
