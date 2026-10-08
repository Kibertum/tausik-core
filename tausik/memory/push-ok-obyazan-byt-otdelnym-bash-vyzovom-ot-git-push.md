---
slug: push-ok-obyazan-byt-otdelnym-bash-vyzovom-ot-git-push
title: "push-ok ОБЯЗАН быть отдельным bash-вызовом от git push (PreToolUse gate проверяет до выполнения)"
type: gotcha
tags:
  - git
  - gotcha
  - hook
  - push-ok
task: null
edges: []
---

git_push_gate.py — PreToolUse Bash hook: инспектирует строку команды ДО выполнения. `tausik push-ok && git push` или `push-ok; git push` в ОДНОЙ команде блокируется — ticket ещё не создан в момент проверки хука. Правильно: `tausik push-ok` одним bash-вызовом (пишет .push_ticket.json, TTL 60s, single-use, bound к commit SHA), затем `git push origin main` СЛЕДУЮЩИМ отдельным вызовом. Между вызовами уложиться в 60s. Связано с [[push-ticket-flow]].
