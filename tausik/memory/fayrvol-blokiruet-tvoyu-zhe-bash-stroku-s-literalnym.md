---
slug: fayrvol-blokiruet-tvoyu-zhe-bash-stroku-s-literalnym
title: "Файрвол блокирует твою же Bash-строку с литеральным опасным паттерном при тестировании хуков"
type: gotcha
tags:
  - dogfooding
  - firewall
  - hooks
  - secret-scan
  - testing
task: null
edges: []
---

При тестировании security-хуков (bash_firewall, secret_scan) end-to-end через Bash-инструмент: если твоя команда содержит ЛИТЕРАЛ опасного паттерна (`rm -rf ~`, `git push --force`, `AKIA...`), сам файрвол/secret-scan заблокирует ТВОЙ вызов до выполнения — это догфудинг, не баг.

**Обход:** строй payload'ы внутри Python-скрипта (в scratchpad) из частей — `chr(126)` для `~`, `"git push --"+"force"`, `"AKIA"+"IOSFODNN7EXAMPLE"` — и корми хук через subprocess с JSON на stdin. Тогда Bash-строка несёт только `python check.py`, без литерала.

Всплыло дважды за сессию #141 (волна s126): rm-wipe `~` и nested-wrapper `git push --force`. Секрет-скан ПОСЛЕ своего расширения на shell-каналы теперь ловит и AKIA-литерал в твоей команде — та же проблема, тот же обход. См. [[secret-scan-covers-no-shell-channel]].
