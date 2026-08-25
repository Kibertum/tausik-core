---
slug: cli-i-mcp-gruzyat-claude-scripts-ne-root-scripts-pravki
title: "CLI и MCP грузят .claude/scripts/ (не root scripts/) — правки source требуют bootstrap + рестарт IDE"
type: gotcha
tags:
  - bootstrap
  - claude-scripts
  - deploy
  - gotcha
  - mcp
task: null
edges: []
---

И MCP-сервер, и CLI-wrapper (.tausik/tausik) исполняют из .claude/scripts/ — генерируемой копии, НЕ из root scripts/. Доказательство: после bump scripts/tausik_version.py до 1.5.0 даже CLI update-claudemd показывал 1.4.0, пока не прогнал bootstrap. Цепочка для деплоя правки source в рантайм: (1) edit root scripts/, (2) python bootstrap/bootstrap.py --ide all (копирует в .claude/.cursor/.qwen; .claude gitignored), (3) рестарт IDE (running MCP-сервер держит старые модули в памяти; не в watched_modules → self_check drift не видит). pytest работает с root scripts/ напрямую (sys.path), поэтому тесты зелёные ≠ рантайм обновлён. Связано с [[any-subprocess-needs-stdin-devnull]].
