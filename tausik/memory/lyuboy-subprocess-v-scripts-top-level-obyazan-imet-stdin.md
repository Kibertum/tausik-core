---
slug: lyuboy-subprocess-v-scripts-top-level-obyazan-imet-stdin
title: "Любой subprocess в scripts/ top-level обязан иметь stdin=DEVNULL (иначе MCP task_done/verify виснет на Windows)"
type: gotcha
tags:
  - hang
  - mcp
  - stdin
  - subprocess
  - task_done
  - verify
  - windows
task: fix-risk-compute-stdin-hang
edges: []
---

Всё в scripts/ top-level MCP-достижимо (импортируется project-сервером). Под MCP sys.stdin = JSON-RPC пайп к IDE; git/любой subprocess без stdin=DEVNULL на Windows читает его (paginator/credential probe) → блок/съедание протокола → silent hang task_done/verify. Класс возвращался дважды: сначала verify_git_diff (фикс v14b-defect-mcp-task-done-stdin-hang), потом risk_compute (v15-risk-compute-on-done реоткрыл, fix-risk-compute-stdin-hang). Защита: test_risk_compute_stdin::TestNoUnguardedSubprocessInMcpPath — AST-скан scripts/*.py на subprocess-вызовы без stdin. scripts/hooks/ исключены (отдельные процессы харнесса). Диагностика: faulthandler-репро в обычном процессе НЕ ловит — баг только когда stdin=MCP-пайп. ВАЖНО: risk_compute.py НЕ в watched_modules → self_check drift не видит его устаревания; после фикса нужен рестарт IDE, иначе running-сервер держит старый код и продолжает виснуть.
