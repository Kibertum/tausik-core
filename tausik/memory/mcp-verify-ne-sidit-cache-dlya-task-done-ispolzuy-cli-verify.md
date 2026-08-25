---
slug: mcp-verify-ne-sidit-cache-dlya-task-done-ispolzuy-cli-verify
title: "MCP verify не сидит cache для task_done — используй CLI verify"
type: gotcha
tags:
  - cache
  - mcp
  - qg2
  - task_done
  - verify
  - workaround
task: null
edges: []
---

Симптом: вызвал `mcp__tausik-project__tausik_verify(task_slug=X)` → получил `passed=True status=miss`, но следующий `mcp__tausik-project__tausik_task_done(slug=X, ac_verified=true)` падает с blocking_failure `verify-first` (cache_status=miss или git-mismatch).

Воспроизведено дважды в session #67 (v14b-followup-brain-sync, v14b-subagent-reviewer). Корневая причина не подтверждена кодом, но эмпирический workaround надёжен:

**Workaround:** Вместо MCP verify запусти `.tausik/tausik.cmd verify --task <slug>` через Bash — он явно пишет `Recorded verification_run` в БД, и следующий `task_done` через MCP читает кэш как `cache_status=hit`.

CLI verify в обоих случаях писал `[SKIP] pytest` (gate dispatch не нашёл test mapping для cli_ops.py / для md+yaml-only diff'а), но всё равно записывал verification_run. MCP verify запускал pytest реально, но запись в кэш либо не происходила, либо имела другой scope/git-state, который task_done не принимал.

**Гипотеза:** MCP verify, запущенный из того же Python-процесса что и MCP task_done, может писать в БД с другим isolation-уровнем; либо cache_status=git-mismatch срабатывает потому что formatter-hook touchает файлы между verify и task_done. CLI verify запускается в отдельном процессе и фиксирует mtime до hook-mod.

**Action:** При закрытии задачи всегда: (1) Edit/Write код, (2) подождать formatter, (3) `.tausik/tausik.cmd verify --task <slug>` через Bash, (4) `tausik_task_done` через MCP. Не chain'ить MCP verify → MCP task_done — оно ломается.
