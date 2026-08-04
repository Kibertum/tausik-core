---
slug: pereklyuchenie-rabochego-dereva-na-staruyu-reviziyu
title: "Переключение рабочего дерева на старую ревизию ОТКЛЮЧАЕТ хуки агента"
type: gotcha
tags:
  - git
  - hooks
  - mirror
  - release-18
task: null
edges: []
---

Хуки Claude Code запускаются как CLAUDE_PROJECT_DIR/scripts/hooks/*.py — то есть из РАБОЧЕГО ДЕРЕВА. git checkout на старую ревизию убирает файл хука, харнесс получает ошибку запуска и блокирует ВСЕ вызовы Bash и PowerShell. Инструмент, которым чинят, отказывает раньше, чем видишь причину.

Поймано вживую в сессии #165: попытка собрать снимок релиза переключением на github/main (в 1.7 нет scripts/hooks/bash_write_gate.py, он появился в 1.8).

Выход, если уже попал: MCP-инструменты хуками НЕ перехватываются. Через MCP: session_end, session_start (иначе гейт ёмкости), task_start — появляется активная задача, Write разрешён, им восстанавливаешь файл хука, Bash оживает. Дальше git checkout -f вернёт дерево.

Как не попадать: снимок для зеркала собирают ПЛАМБИНГОМ, не трогая рабочее дерево:
  export GIT_INDEX_FILE=<вне репозитория>
  git read-tree <ref>
  git ls-files --cached -- <каталог> | grep -v <что оставить> > drop.txt
  git update-index --force-remove --stdin < drop.txt
  TREE=$(git write-tree); unset GIT_INDEX_FILE
  COMMIT=$(git commit-tree $TREE -p github/main -F msg.txt)
  git update-ref refs/heads/<ветка> $COMMIT
