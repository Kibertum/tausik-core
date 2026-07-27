---
slug: retro-28-installed-vs-source-layout-trebuet-runtime-smoke
title: "Retro #28: installed vs source layout — требует runtime smoke-теста"
type: pattern
tags:
  - bootstrap
  - gap
  - mcp
  - testing
task: null
edges: []
---

Уже 3-й баг с расхождением layout (`agents/...` source vs `.claude/...` installed). bootstrap_generate_mcp тест покрывает генерацию файлов, но не проверяет, что они запускаются. Нужен test_bootstrap_mcp_runtime.py: после bootstrap делает subprocess-импорт .claude/mcp/brain/handlers.py. Перекроет path arithmetic, missing imports, sys.path коллизии за один прогон.
