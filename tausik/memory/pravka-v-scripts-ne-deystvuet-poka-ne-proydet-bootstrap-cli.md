---
slug: pravka-v-scripts-ne-deystvuet-poka-ne-proydet-bootstrap-cli
title: "Правка в scripts/ НЕ действует, пока не пройдёт bootstrap: CLI и MCP исполняют .claude/scripts/, а тесты импортируют scripts/"
type: gotcha
tags:
  - bootstrap
  - deployment
  - gates
  - measurement
task: claudemd-drift-gates-do-not-notice-an-emptied-dynamic-block
edges: []
---

ЗАМЕРЕНО #191-БД. Обёртка `.tausik/tausik` выбирает первый существующий каталог из `.claude/scripts`, `.cursor/scripts`, `.windsurf`, `.codex`, `.qwen`, `.kilo`, `.opencode` и исполняет код ОТТУДА. MCP-сервер — так же. А тесты делают `sys.path.insert(0, 'scripts')` и импортируют ИСТОЧНИК.

СЛЕДСТВИЕ, КОТОРОЕ ЛОВИТ ЛЮБОГО: после правки scripts/gate_registry.py тесты зелёные, `tausik gates status` НОВОГО ГЕЙТА НЕ ПОКАЗЫВАЕТ, а `task done` его не запускает. Обе стороны не врут — они говорят о разном коде.

ПРОВЕРКА И ЛЕКАРСТВО, ОБЕ ОДНОЙ КОМАНДОЙ:
  python bootstrap/bootstrap.py --project-dir . --ide all --check   # только отчёт, ничего не пишет
  python bootstrap/bootstrap.py --project-dir . --ide all           # развернуть
`--check` перечисляет дрейфующие файлы по всем пяти профилям и заканчивается строкой «no bootstrap drift; deployed profiles match source».

ЗАМЕР ПОБОЧНЫЙ И ВАЖНЫЙ: bootstrap БЕЗ `--init` корневой CLAUDE.md и AGENTS.md НЕ ТРОГАЕТ — sha256 обоих файлов до и после развёртывания пяти профилей совпал (992f3731… и c70c36a9…). То есть штатное развёртывание не является писателем динамического блока.

ПОЧЕМУ ЭТО НЕ ЛОВИТСЯ САМО: гейт bootstrap_drift придуман ровно против этого и в этом проекте стоит [OFF] — заведена задача bootstrap-drift-gate-is-off-so-source-edits-never-reach-the-running-cli. До её закрытия разворачивать профиль ПОСЛЕ каждой правки scripts/ — ручная обязанность.
