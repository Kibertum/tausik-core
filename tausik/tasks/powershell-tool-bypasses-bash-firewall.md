---
slug: powershell-tool-bypasses-bash-firewall
title: "Основная оболочка на Windows не проходит ни одного хука: весь firewall защищает Bash-инструмент, а работа идёт через PowerShell"
status: done
epic: null
story: null
complexity: complex
role: architect
stack: python
tier: substantial
call_budget: 120
defect_of: null
scope: "scripts/hooks/*.py, bootstrap/bootstrap_hooks.py, tests/test_*.py, docs/ru/*.md, docs/en/*.md, CHANGELOG.md, CHANGELOG.ru.md"
scope_exclude: ".claude/** (генерируется из bootstrap), .tausik/**, набор _WIPE_ROOTS в части ~/*/.. (задача firewall-rm-wipe-targets-policy)"
relevant_files:
  - "scripts/hooks/pwsh_cmd_parse.py"
  - "scripts/hooks/pwsh_cmd_norm.py"
  - "scripts/hooks/pwsh_write_parse.py"
  - "scripts/hooks/shell_channel.py"
  - "scripts/hooks/danger_patterns.py"
  - "scripts/hooks/bash_cmd_scan.py"
  - "scripts/hooks/write_confidence.py"
  - "scripts/hooks/bash_firewall.py"
  - "scripts/hooks/bash_write_gate.py"
  - "scripts/hooks/bash_write_parse.py"
  - "scripts/hooks/git_push_gate.py"
  - "scripts/hooks/memory_pretool_block.py"
  - "scripts/hooks/rm_wipe_detect.py"
  - "bootstrap/bootstrap_hooks.py"
  - "bootstrap/bootstrap_qwen.py"
  - "tests/test_powershell_channel.py"
  - "tests/test_bootstrap_hooks_parity.py"
  - "tests/test_memory_pretool_block_hook.py"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - README.md
  - README.ru.md
  - "docs/_generated/constants.json"
  - "docs/en/hooks.md"
  - "docs/en/security.md"
  - "docs/en/enforcement-coverage.md"
  - "docs/ru/agent-contract.md"
  - "docs/ru/enforcement-coverage.md"
  - "docs/ru/hooks.md"
  - "docs/ru/security.md"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-24T12:00:32Z"
---

## Goal

Находка adversarial-ревью сессии #133, подтверждённая наблюдением. .claude/settings.json регистрирует bash_firewall.py с "matcher": "Bash". На win32-хосте (а это ПЕРВИЧНАЯ платформа проекта — CLAUDE.md, docs, .cmd-обёртка) агенту доступен отдельный инструмент PowerShell, который не матчится НИ ОДНИМ PreToolUse-хуком. Ревьюер зафиксировал это побочно: его пробу через Bash остановил bash_write_gate, а идентичная работа через PowerShell прошла без перехвата. Следствия: (1) Remove-Item -Recurse -Force не проверяется вообще; (2) _RM_WIPE_TARGETS содержит только POSIX-корни, `C:\`, `D:\`, `/c/` отсутствуют; (3) Rule 1 (задача перед кодом) и Rule 2 (scope ACL) для записи через PowerShell тоже не действуют, если запись идёт Set-Content/Out-File. То есть вся работа сессии #133 по firewall имеет ценность в основном как переносимость на POSIX-хосты, а локально надзор дырявый по КАНАЛУ, а не по правилу. Это надо либо закрыть (matcher на PowerShell + разбор её команд), либо честно объявить в доках, что защита покрывает только Bash-канал — молчать нельзя: сейчас документация создаёт впечатление сплошного покрытия. Первым шагом ИЗМЕРИТЬ: перечислить все PreToolUse-хуки и их matcher'ы, и для каждого сказать, что происходит с эквивалентной PowerShell-командой.

## Acceptance Criteria

AC-1 (замер зафиксирован): для КАЖДОГО PreToolUse-хука названо, что происходит с эквивалентной PowerShell-командой. Замер уже дал восьмой пункт, которого нет в goal: git_push_gate тоже висит на Bash, т.е. `git push --force` через PowerShell не гейтится ничем. Результат — таблица в доках, не в голове.

AC-2 (канал закрыт в регистрации): enforcement-хуки (task_gate, scope_write_gate, memory_pretool_block, secret_scan, bash_firewall, bash_write_gate, git_push_gate) матчатся на инструмент PowerShell. Правка в bootstrap/bootstrap_hooks.py (источник), НЕ в .claude/. Тест паритета bootstrap↔deployed зелёный.

AC-3 (канал закрыт в самих хуках): хуки принимают tool_name == "PowerShell", а не только "Bash". Пин: сейчас даже с matcher'ом они вернут 0 из-за `event.get("tool_name") != "Bash"` — тест должен падать на текущем коде.

AC-4 (разбор диалекта): новый модуль разбора PowerShell — алиасы (rm/del/ri/rd/rmdir/erase→Remove-Item, sc→Set-Content, ac→Add-Content, ni→New-Item, echo→Write-Output), сокращения параметров PowerShell (-Rec/-Recu/-Fo — префиксное сокращение легально и должно ловиться), разделители (;, |, &&, ||, перевод строки), вложенные обёртки (powershell -Command "...", pwsh -c, iex/Invoke-Expression, cmd /c, bash -c внутри PowerShell).

AC-5 (wipe): Remove-Item -Recurse -Force по корню тома (C:\, C:/, D:\) и по POSIX-корню блокируется. Набор «что считается корнем» — ОДНА общая функция-судья на оба диалекта (конв. #266/#289: не вторая копия правила), два дialect-специфичных парсера флагов над ней. Вопросы `~`, `*`, `..` НЕ решаются здесь — они принадлежат задаче firewall-rm-wipe-targets-policy.

AC-6 (write): запись через Set-Content / Add-Content / Out-File / New-Item -ItemType File / > / >> / Tee-Object детектится и проходит те же QG-0 (Rule 1) и scope-ACL (Rule 2), что и инструмент Write — переиспользованием решения scope_write_gate, а не копией.

AC-7 (push): git push через PowerShell доходит до git_push_gate и получает тот же вердикт, что через Bash.

AC-8 (негативные пины — цена ошибки, конв. #291): честная работа НЕ блокируется. Минимум: Remove-Item -Recurse подкаталога проекта, Get-Content/Select-String, цитата опасной команды внутри строкового литерала, `Set-Content` в разрешённый scope при активной задаче.

AC-9 (дифференциальный прогон, конв. #298): судья корней меняется → старая и новая реализации прогоняются на ОБЩЕМ наборе операндов, расхождения печатаются в ОБЕ стороны. Фраза «поведение POSIX-канала не изменилось» пишется только по результату этого прогона.

AC-10 (честность доков, конв. #282/#297): матрица покрытия каналов в docs — что гейтится, что нет, остаточная граница названа явно. Молчание запрещено: контракт AC2 допускает «закрыть ИЛИ объявить границу», но не умолчание.

AC-11: полный pytest зелёный (не scoped — хэндофф #133 трижды показал, что scoped даёт ложный зелёный на хуках/гейтах).

## Plan

## Rollback

git revert коммита. Изменения аддитивны: новые модули pwsh_*.py удаляются, matcher'ы в bootstrap_hooks.py возвращаются к "Bash", .claude/ перегенерируется bootstrap'ом. Ни одна существующая POSIX-ветка не переписывается — общая функция-судья выносится рефакторингом с дифференциальным прогоном (AC-9), поэтому откат не оставляет полусостояния.

## Journal

- 2026-07-24T11:29:31Z [implementation] — Adversarial-ревью СВОЕГО фикса (конв. #276) нашло два дефекта, оба в новом коде. (1) Я раскритиковал перечисление каналов и сам захардкодил `== "PowerShell"` в bash_firewall — вторая карта того же множества. Вынес POSIX-сканер в bash_cmd_scan.py, карта диалектов теперь одна в shell_channel (_DIALECTS + _SCANNERS, сверены тестом). (2) НАСТОЯЩАЯ ДЫРА: `powershell -Command 'Remove-Item -Recurse -Force C:\'` через Bash проходил (rc=0). Сканер склеивает токены и снимает кавычки — после этого `-Command` связывает только первое слово, а операнд рассыпается в позиционные статемента с verb=`-Command`. Починка: структурного PowerShell-судью спрашиваем И по СЫРОЙ строке. POSIX-судью по сырой строке спрашивать НЕЛЬЗЯ — он regex и заблокировал бы `git commit -m 'Remove-Item ... C:\'`; три негативных пина держат эту границу. Плюс переименовал danger_patterns.wiped_root -> wiped_root_any: одноимённая функция с другой сигнатурой рядом с rm_wipe_detect.wiped_root — ловушка того же класса, что чиню.
- 2026-07-24T11:42:36Z [implementation] — AC-1 замер: таблица 7 хуков в docs/ru/agent-contract.md + восьмой пункт (git_push_gate) найден замером, в goal его не было. AC-2/AC-7 матчеры SHELL_MATCHER в bootstrap_hooks.py и bootstrap_qwen.py, клауза if снята; tests/test_bootstrap_hooks_parity.py::test_every_shell_gate_is_registered_for_every_shell_tool. AC-3 shell_channel.command_of/SHELL_TOOLS вместо литерала != Bash; tests/test_powershell_channel.py::TestGatesActuallyFireOnTheChannel. AC-4 pwsh_cmd_parse+pwsh_cmd_norm; tests/test_powershell_channel.py::TestParameterAbbreviation. AC-5 rm_wipe_detect.is_wipe_root один судья; tests/test_powershell_channel.py::TestOneJudgeTwoDialects::test_both_dialects_ask_the_same_judge. AC-6 pwsh_write_parse; tests/test_powershell_channel.py::TestWriteTargets. AC-8 негативные пины; tests/test_powershell_channel.py::TestWipeDetection::test_honest_work_is_not_blocked и TestCrossChannelWrappers::test_a_quoted_mention_survives_the_raw_line_judge. AC-9 дифференциальный прогон: 0 сужений, 11 расширений (только корни тома); tests/test_powershell_channel.py::TestOneJudgeTwoDialects::test_widening_is_exactly_the_volume_roots. AC-10 матрица покрытия в docs/ru/agent-contract.md + hooks.md/security.md EN+RU, secret_scan-пробел назван явно и заведён задачей. AC-11 полный pytest 5736 passed, 23 skipped.
- 2026-07-24T11:45:28Z [implementation] — AC-1: tests/test_bootstrap_hooks_parity.py::test_every_shell_gate_is_registered_for_every_shell_tool + таблица 7 хуков в docs/ru/agent-contract.md; замер дал восьмой пункт (git_push_gate), которого в goal не было. AC-2: tests/test_bootstrap_hooks_parity.py::test_shell_matcher_covers_every_dialect_the_parser_knows. AC-3: tests/test_powershell_channel.py::TestGatesActuallyFireOnTheChannel::test_firewall_blocks_a_volume_wipe. AC-4: tests/test_powershell_channel.py::TestParameterAbbreviation::test_recurse_abbreviations_all_register. AC-5: tests/test_powershell_channel.py::TestOneJudgeTwoDialects::test_both_dialects_ask_the_same_judge. AC-6: tests/test_powershell_channel.py::TestWriteTargets::test_write_vectors_are_seen. AC-7: tests/test_powershell_channel.py::TestGatesActuallyFireOnTheChannel::test_push_gate_sees_a_push_from_powershell. AC-8: tests/test_powershell_channel.py::TestWipeDetection::test_honest_work_is_not_blocked. AC-9: tests/test_powershell_channel.py::TestOneJudgeTwoDialects::test_widening_is_exactly_the_volume_roots. AC-10: tests/test_powershell_channel.py::TestOneDialectTableNotTwo::test_the_firewall_does_not_spell_the_channel_list_itself. AC-11: полный pytest 5736 passed, 23 skipped; verification_run #1271 pytest PASS 24562 ms.
- 2026-07-24T12:00:30Z [implementation] — AC-1: tests/test_bootstrap_hooks_parity.py::test_every_shell_gate_is_registered_for_every_shell_tool + матрица 7 хуков в docs/ru/enforcement-coverage.md; замер дал восьмой пункт (git_push_gate), которого в goal не было. AC-2: tests/test_bootstrap_hooks_parity.py::test_shell_matcher_covers_every_dialect_the_parser_knows. AC-3: tests/test_powershell_channel.py::TestGatesActuallyFireOnTheChannel::test_firewall_blocks_a_volume_wipe. AC-4: tests/test_powershell_channel.py::TestParameterAbbreviation::test_recurse_abbreviations_all_register. AC-5: tests/test_powershell_channel.py::TestOneJudgeTwoDialects::test_both_dialects_ask_the_same_judge. AC-6: tests/test_powershell_channel.py::TestWriteTargets::test_write_vectors_are_seen. AC-7: tests/test_powershell_channel.py::TestGatesActuallyFireOnTheChannel::test_push_gate_sees_a_push_from_powershell. AC-8: tests/test_powershell_channel.py::TestWipeDetection::test_honest_work_is_not_blocked + TestCrossChannelWrappers::test_a_quoted_mention_survives_the_raw_line_judge. AC-9: tests/test_powershell_channel.py::TestOneJudgeTwoDialects::test_widening_is_exactly_the_volume_roots и ::test_no_operand_stopped_being_judged_a_root. AC-10: docs/ru/enforcement-coverage.md + docs/en/enforcement-coverage.md, secret_scan-пробел назван явно и заведён задачей secret-scan-covers-no-shell-channel. AC-11: полный pytest 5736 passed 23 skipped; verification_run #1273 pytest PASS 25875 ms.
- 2026-07-24T12:00:55Z [done] — Negative: негативные сценарии AC прогнаны и запинены, а не только позитивные. (1) Честная работа не блокируется: `Remove-Item -Recurse -Force .\build`, `... C:\Users\me\proj`, `node_modules`, `Remove-Item C:\` БЕЗ -Recurse, `Get-ChildItem C:\ -Recurse` — tests/test_powershell_channel.py::TestWipeDetection::test_honest_work_is_not_blocked. (2) Цитата опасной команды не становится командой: `Write-Output 'Remove-Item -Recurse -Force C:\ is dangerous'`, `Get-Content notes.md | Select-String 'rm -rf /'` — там же. (3) Новый риск, созданный САМИМ фиксом (судья по сырой строке), запинен отдельно: `git commit -m 'Remove-Item ... C:\ must be blocked'`, `powershell -Command 'echo "Remove-Item ..."'`, `tausik memory add 'never Remove-Item ...'` — все rc=0, tests/test_powershell_channel.py::TestCrossChannelWrappers::test_a_quoted_mention_survives_the_raw_line_judge. (4) Второй позиционный аргумент Set-Content — это СОДЕРЖИМОЕ, а не файл: ::test_second_positional_of_set_content_is_content_not_a_file. (5) Непарсящаяся команда не отдаёт пустой список (молчаливое «ничего не пишет»), а падает в regex-fallback с флагом уверенности: ::test_unparseable_command_guesses_rather_than_reporting_nothing. Domain: результат осмыслен вне тестов. Проверено исполнением реальных хук-процессов (subprocess, не импорт функций): bash_firewall.py на событии {"tool_name":"PowerShell","tool_input":{"command":"Remove-Item -Recurse -Force C:\\"}} даёт rc=2 — до задачи давал rc=0. git_push_gate.py на PowerShell-событии с `git push --force` требует push-тикет — до задачи не вызывался вовсе. Дифференциальный прогон судьи корней на 61 операнде показал 0 сужений и 11 расширений, и все 11 — написания корня тома (C:\, C:/, D:\, C:\*, C:/./), то есть на POSIX-хостах поведение буквально не изменилось, а на win32 появился корень, которого детектор не мог назвать. Ложное срабатывание на `C:` физически недостижимо в Windows: двоеточие запрещено в именах файлов, поэтому `C:` не может означать относительный каталог.
