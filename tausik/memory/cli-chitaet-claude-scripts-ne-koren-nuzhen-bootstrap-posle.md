---
slug: cli-chitaet-claude-scripts-ne-koren-nuzhen-bootstrap-posle
title: "CLI читает .claude/scripts, не корень — нужен bootstrap после правки scripts/"
type: gotcha
tags:
  - bootstrap
  - cli
  - dev-workflow
  - mcp
task: null
edges: []
---

CLI wrapper `.tausik/tausik` (и `.tausik/tausik.cmd`) указывают на `.claude/scripts/` (или `.cursor/scripts/`), не на корневой `scripts/`. После любой правки `scripts/*.py` нужно запустить `python bootstrap/bootstrap.py --no-detect` чтобы синхронизировать `.claude/scripts/`.

Симптом: правка работает в `python -c "sys.path.insert(0,'scripts'); from X import ..."` (использует корень), но `.tausik/tausik <cmd>` использует старый код и зависает / даёт wrong behavior.

Также: MCP-сервер запускается из `.claude/mcp/project/server.py` — bootstrap копирует и его код. Но запущенный MCP-сервер кеширует модули в памяти; для применения нужен рестарт окна редактора (новый Claude Code → новый MCP).

Workflow: edit scripts/ → bootstrap → restart editor (для MCP) ИЛИ использовать CLI после bootstrap (для свежего процесса).
