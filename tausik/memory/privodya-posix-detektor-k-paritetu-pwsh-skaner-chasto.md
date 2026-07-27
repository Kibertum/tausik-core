---
slug: privodya-posix-detektor-k-paritetu-pwsh-skaner-chasto
title: "Приводя POSIX-детектор к паритету, pwsh-сканер — часто готовый референс (и наоборот)"
type: pattern
tags:
  - architecture
  - hooks
  - parity
  - posix
  - powershell
  - security
task: null
edges: []
---

Два канала (POSIX bash_cmd_* и PowerShell pwsh_cmd_*) должны судить одинаково (конв #266/#289). Когда находишь дыру на одной стороне, ПРОВЕРЬ, не решена ли она уже на другой — часто да, и тогда фикс = ПОРТ проверенного кода, а не новый парсинг (а новый shell-парсинг породил КАЖДУЮ регрессию в hooks/ — см. заголовки rm_wipe_detect/bash_cmd_norm).

Пример (сессия #141, [[nested-wrapper-non-shell-interpreters]]): POSIX descent `_shell_payloads` знал 7 шеллов, а raw-join `_INTERPRETERS` — 34; вложенная команда за внутренней кавычкой в powershell/cmp-обёртке проходила. pwsh_cmd_norm.payloads УЖЕ спускался во весь свой интерпретаторный набор (-Command/-c//c/k) — фикс свёлся к порту этой логики (`_interpreter_payloads`), не к изобретению.

Симметрия работает в обе стороны: is_wipe_root — ОДИН судья для обоих каналов; добавив `~`, покрыл и `Remove-Item -Recurse ~` бесплатно. Остатки тоже держи симметричными: ssh/wsl не спускаются НИ на одной стороне.
