---
slug: parnye-sessii-zamery-gonyayutsya-bezgolovym-claude-code-iz
title: "Парные сессии-замеры гоняются безголовым Claude Code из Bash, а не двумя ручными сессиями IDE"
type: pattern
tags:
  - benchmark
  - claude-code
  - headless
  - windows
  - worktree
task: v14b-rag-nudge-replay-benchmark
edges: []
---

Бинарь claude.exe лежит в расширении VS Code (~/.vscode/extensions/anthropic.claude-code-<ver>-win32-x64/resources/native-binary/), в PATH его нет. `claude -p --verbose --input-format stream-json --output-format stream-json --model claude-opus-5[1m] --mcp-config .mcp.json --strict-mcp-config --allowedTools … --disallowedTools Edit Write Agent --append-system-prompt …` даёт одну сессию с отдельными ходами: драйвер пишет следующий user-JSON в stdin только после события result предыдущего. Транскрипт — ~/.claude/projects/<slug-cwd>/<session_id>.jsonl, окно смены TAUSIK через session_windows.make_session_resolver. Три ловушки: (1) запускать драйвер ОТДЕЛЬНО от инструмента Bash (PowerShell Start-Process), иначе 10-минутный таймаут инструмента убьёт прогон; (2) в worktree нет .tausik/ и .claude/ — БД копировать sqlite backup(), rag/ копировать (paths относительные), venv — junction, затем bootstrap там; (3) чистоту условия «без подсказок» доказывать по транскрипту (ноль вхождений текстов), а не по списку мест впрыска — список протокола отстал на два места. Полный замер: 6 мест впрыска, 10 вопросов, ~9 мин и ~200 k новых токенов на условие. Скрипты: docs/ru/research/_internal/rag-replay/2026-09-14/replay_{driver,metrics,compare}.py.
