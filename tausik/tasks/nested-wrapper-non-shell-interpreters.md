---
slug: nested-wrapper-non-shell-interpreters
title: "Спуск во вложенную обёртку работает для 7 оболочек из 34 интерпретаторов: ssh/powershell/cmd/wsl по-прежнему прячут команду"
status: done
epic: null
story: null
complexity: medium
role: developer
stack: python
tier: moderate
call_budget: 50
defect_of: null
scope: "scripts/hooks/bash_cmd_norm.py (новый _interpreter_payloads), scripts/hooks/bash_cmd_scan.py (использовать его в descent + докстринг), tests/test_hooks.py (пины: powershell/pwsh/cmd blocked, ssh/wsl residual)"
scope_exclude: "scripts/hooks/bash_write_parse.py (_shell_payloads не трогать — блокирующий гейт), pwsh_cmd_norm.py (референс, уже корректен)"
relevant_files:
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - CLAUDE.md
  - README.md
  - README.ru.md
  - "bootstrap/bootstrap_hooks.py"
  - "bootstrap/bootstrap_qwen.py"
  - "docs/_generated/constants.json"
  - "docs/en/enforcement-coverage.md"
  - "docs/ru/enforcement-coverage.md"
  - "scripts/hooks/bash_cmd_norm.py"
  - "scripts/hooks/bash_cmd_scan.py"
  - "scripts/hooks/rm_wipe_detect.py"
  - "scripts/hooks/secret_scan.py"
  - "tests/test_hooks.py"
  - "tests/test_secret_scan_hook.py"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-26T16:05:37Z"
---

## Goal

Находка adversarial-ревью сессии #133 на фикс bash-firewall-lacks-command-normalization, воспроизведена: `ssh host "sh -c 'git push --force'"` и `powershell -c "powershell -c 'git push --force'"` дают WARN=[] — то есть проходят. Тот же корень, что у закрытой дыры: внутренняя кавычка выживает в raw-склейке и ломает якорь начала команды. Спуск в payload происходит только когда его распознаёт bash_cmd_norm._shell_payloads, а там 7 оболочек {bash, sh, zsh, dash, ksh, ash, busybox}, тогда как raw-склейку ЗАПУСКАЕТ _INTERPRETERS из 34 имён, включая cmd, powershell, pwsh, wsl, ssh. Для остальных 27 спуска нет. Докстринг при этом утверждает «a shell payload is now RE-SCANNED as the command line it is» без оговорки — заявление шире построенного, и добавленные тесты (bash/sh + env/sudo) выглядят как полное покрытие. На win32-хосте вложенность через powershell вероятнее, чем через bash -c. Задача: либо расширить извлечение payload на форму `-Command`/`-c` для powershell/cmd/wsl и на `ssh host '<cmd>'`, либо сузить утверждение в докстринге и назвать остаток тестом-пином. Для ssh отдельно решить: пути и политика чужого хоста здесь не значат ничего (это уже записано как остаток в bash_write_parse) — возможно, правильный ответ «не спускаться, но и не утверждать, что спускаемся».

## Acceptance Criteria

1. Вложенные локальные обёртки, прятавшие команду за внутренней кавычкой, теперь ловятся POSIX-сканером: `powershell -c "powershell -c 'git push --force'"`, `pwsh -Command "sh -c '...'"`, `cmd /c "sh -c '...'"` → exit 2 (через Bash-инструмент). 2. Механизм — паритет с pwsh_cmd_norm.payloads (референс): descent bash_cmd_scan расширен на command-несущие интерпретаторы (powershell/pwsh -c/-Command, cmd /c//k), а не только 7 POSIX-шеллов. 3. ssh и wsl остаются НЕспускаемым остатком (чужой хост / нет -c формы) — СИММЕТРИЧНО с pwsh-стороной, которая их тоже не спускает; названы явно и запинены тестом. 4. Завышенный докстринг bash_cmd_scan.scan_target («a shell payload is now RE-SCANNED») сужен: перечислено, что спускается, а что остаток. 5. Блокирующий scope/write-гейт (bash_write_parse) НЕ затронут (риск ложных BLOCK нулевой) — _shell_payloads без изменений. 6. Полная суита зелёная, 0 warnings.

## Plan

## Rollback

git revert; изменение аддитивное (новая функция + смена вызова в scan_target descent) — откат восстанавливает _shell_payloads-descent.

## Journal

- 2026-07-26T16:05:35Z [implementation] — AC verified: 1. ✓ test_hooks.py::test_command[nested_powershell_wrapper_push_force_blocked|nested_pwsh_command_reset_hard_blocked|nested_cmd_slashc_rm_blocked|nested_powershell_wrapper_git_clean_blocked] all exit 2 (were rc=0 before) 2. ✓ _interpreter_payloads in bash_cmd_norm.py adds powershell/pwsh -c/-Command + cmd /c//k descent; mirrors pwsh_cmd_norm.payloads 3. ✓ ssh_remote_nested_payload_residual_allowed + wsl_nested_payload_residual_allowed both exit 0 (pinned residual, symmetric with pwsh side) 4. ✓ bash_cmd_scan.scan_target docstring narrowed — lists descended interpreters vs named residuals (ssh/wsl/lang -c/-EncodedCommand) 5. ✓ _shell_payloads unchanged; bash_write_parse import/use untouched; powershell_echo_of_force_push_still_allowed exit 0 (no false positive) 6. ✓ tausik_verify high pytest PASS over 4 mapped files; test_hooks+powershell_channel+gate_shellless 263 passed; profiles redeployed; constants matching 7. ✓ Domain: a real nested powershell/cmd wrapper around git push --force / rm -rf / is now blocked pre-exec on the Bash channel; genuine data in a wrapper still passes; remote ssh correctly out of scope. Negative: powershell_echo_of_force_push_still_allowed pins that quoted data does not false-block
