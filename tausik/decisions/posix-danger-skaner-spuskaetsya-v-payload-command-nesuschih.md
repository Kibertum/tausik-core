---
slug: posix-danger-skaner-spuskaetsya-v-payload-command-nesuschih
task: nested-wrapper-non-shell-interpreters
date: "2026-07-26"
edges: []
---

## Decision

POSIX danger-сканер спускается в payload command-несущих интерпретаторов (powershell/pwsh -c/-Command, cmd /c//k) через новый _interpreter_payloads — паритет с уже корректным pwsh_cmd_norm.payloads. ssh и wsl НЕ спускаются (остаток, симметрично обеим сторонам). Блокирующий write/scope-гейт не трогаем.

## Rationale

Корень: bash_cmd_scan raw-склеивает 34 интерпретатора (_INTERPRETERS), но descent _shell_payloads знает только 7 POSIX-шеллов, поэтому вложенная команда за ВНУТРЕННЕЙ кавычкой (`powershell -c "powershell -c 'git push --force'"`) через Bash-инструмент не переспускается: перед inner `git` стоит апостроф, который _CMD_START не принимает, WARN-паттерны молчат, а descent не идёт. pwsh_cmd_norm.payloads УЖЕ решил это правильно на своей стороне (извлекает -Command/-c//c/k для всего интерпретаторного набора), так что это не новый парсинг, а ПОРТ проверенного референса на POSIX-сторону — принцип «одно поведение, оба канала» (конв. #266/#289). ssh: `ssh host '<cmd>'` исполняется на ЧУЖОМ хосте, чьи пути и git-remote этот файрвол осмыслить не может; спуск заявлял бы защиту, которую честно не даём. У ssh нет -c формы, поэтому token-loop его позитионал и не берёт — остаётся остатком АВТОМАТИЧЕСКИ и СИММЕТРИЧНО (pwsh payloads тоже не берёт ssh-позиционал). wsl: нет стандартной -c формы (args -e/--exec/позиционал = linux-команда) — тот же остаток на обеих сторонах. Язык-интерпретаторы (python/perl/ruby -c) исключены из точного извлечения: их -c это КОД, а не командная строка оболочки; переспуск кода как shell — шум (over-scan безопасен, но точность лучше), назван остатком. Область изменения ограничена danger-сканером: _shell_payloads (используемый bash_write_parse) НЕ трогаю, чтобы блокирующий scope/write-гейт (exit 2, без approval) не получил ложных срабатываний — danger-скан преимущественно WARN с TAUSIK_SKIP_HOOKS-эскейпом, у него постура over-detect, у блок-гейта — точность. Две функции с разной постурой риска — осознанно, задокументировано.
