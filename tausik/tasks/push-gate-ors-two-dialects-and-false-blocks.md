---
slug: push-gate-ors-two-dialects-and-false-blocks
title: "git_push_gate читает строку ОБОИМИ токенизаторами и блокирует, если хоть один увидел push — POSIX-лексер неверно читает PowerShell и находит push в прозе commit-сообщения"
status: done
epic: null
story: null
complexity: simple
role: developer
stack: python
tier: null
call_budget: null
defect_of: powershell-tool-bypasses-bash-firewall
scope: "scripts/hooks/git_push_gate.py, scripts/hooks/shell_channel.py, scripts/hooks/bash_write_parse.py, scripts/hooks/pwsh_write_parse.py, tests/test_powershell_channel.py, CHANGELOG.md, CHANGELOG.ru.md, docs/ru/enforcement-coverage.md, docs/en/enforcement-coverage.md"
scope_exclude: null
relevant_files:
  - "scripts/hooks/git_push_gate.py"
  - "scripts/hooks/shell_channel.py"
  - "scripts/hooks/bash_write_parse.py"
  - "scripts/hooks/pwsh_write_parse.py"
  - "tests/test_powershell_channel.py"
  - "docs/ru/enforcement-coverage.md"
  - "docs/en/enforcement-coverage.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-24T12:47:02Z"
---

## Goal

defect_of powershell-tool-bypasses-bash-firewall, найден догфудингом на следующем же коммите после закрытия предыдущего дефекта.

В рамках закрытия PowerShell-канала я переписал `_command_invokes_git_push` так, что он пробует ОБА токенизатора и возвращает True, если push увидел ЛЮБОЙ. Обоснование в докстринге («нельзя обойти выбором другого инструмента») верно против уклонения, но создаёт ложные срабатывания: каждый диалект неверно читает синтаксис другого.

Наблюдено: `git commit -m @'...'@` через инструмент PowerShell заблокирован с требованием push-тикета. Причина — тело here-string содержало слово «PowerShell's»; POSIX `shlex` не знает here-string, ломается на апострофе, и дальше слова `git push --force` из ПРОЗЫ сообщения становятся отдельными токенами. PowerShell-токенизатор ту же строку читает верно (тело — один токен) и push не видит. Побеждает ошибающийся.

Это тот же класс, что и предыдущий дефект: детекторы для нового канала перенесены, а различение «текст или команда» осталось диалект-специфичным. Разница в том, что здесь ошибка внесена НЕ пропуском защиты, а сознательным ИЛИ между двумя судьями, из которых один заведомо некомпетентен в чужом синтаксисе.

Цена асимметрична и высока: git_push_gate по собственному докстрингу — «дисциплинарный рельс, а не firewall против злонамеренного агента» (эту роль несёт bash_firewall, и force-push он ловит отдельно). Значит ложный блок здесь дороже пропуска, а сейчас блокируется обычный коммит с многострочным сообщением.

Правильный шов уже существует и не задействован: `shell_channel` — единственная карта диалектов. Токенизация должна идти через неё по `tool_name`, как это уже делают write_targets и scan_target. Отдельная проверка: НЕ использовать для этого `scan_target`, он склеивает statement'ы интерпретаторов сырьём и заблокирует честный `python -c "print('git push')"` — то есть внесёт другой ложный блок вместо этого.</goal>
<parameter name="acceptance_criteria">AC-1 (воспроизведение, падает на текущем коде): событие {tool_name: PowerShell} с командой `git commit -m @'...'@`, чьё тело содержит апостроф И слова `git push`, сейчас даёт rc=2 с требованием push-тикета. Пин на реальное тело из заблокированного коммита сессии #134, а не на выдуманное.

AC-2: токенизация идёт через `shell_channel` по `tool_name` — та же единственная карта диалектов, что у write_targets и scan_target. Никакой второй карты и никакого выбора токенизатора в самом гейте.

AC-3: настоящий push по-прежнему ловится на ОБОИХ каналах: `git push --force` через Bash и через PowerShell → rc=2. Существующие пины git_push_gate зелёные без правок.

AC-4 (негативные пины на ложный блок): не блокируются `git commit -m @'...'@` с упоминанием push в теле; `tausik memory add "...git push..."`; `python -c "print('git push')"` — последний важен особо, он проверяет, что фикс НЕ сделан через scan_target, который склеивает payload интерпретатора сырьём.

AC-5 (не открыть дыру взамен): решить и задокументировать, ловится ли push внутри обёртки (`powershell -Command 'git push'` через Bash). Если да — пин; если нет — назвать остаточной границей в enforcement-coverage.md рядом с уже описанными. Молчание запрещено: именно молчаливое допущение и породило исходную задачу.

AC-6: полный pytest зелёный + догфуд: заблокированный коммит проходит.

## Acceptance Criteria

AC-1 (воспроизведение, падает на текущем коде): событие {tool_name: PowerShell} с командой `git commit -m @'...'@`, чьё тело содержит апостроф И слова `git push`, сейчас даёт rc=2 с требованием push-тикета. Пин на реальное тело из заблокированного коммита сессии #134, а не на выдуманное.

AC-2: токенизация идёт через `shell_channel` по `tool_name` — та же единственная карта диалектов, что у write_targets и scan_target. Никакой второй карты и никакого выбора токенизатора в самом гейте.

AC-3: настоящий push по-прежнему ловится на ОБОИХ каналах: `git push --force` через Bash и через PowerShell → rc=2. Существующие пины git_push_gate зелёные без правок.

AC-4 (негативные пины на ложный блок): не блокируются `git commit -m @'...'@` с упоминанием push в теле; `tausik memory add "...git push..."`; `python -c "print('git push')"` — последний важен особо: он проверяет, что фикс НЕ сделан через scan_target, который склеивает payload интерпретатора сырьём и внёс бы другой ложный блок вместо этого.

AC-5 (не открыть дыру взамен): решить и задокументировать, ловится ли push внутри обёртки (`powershell -Command 'git push'` через Bash). Если да — пин; если нет — назвать остаточной границей в enforcement-coverage.md рядом с уже описанными. Молчание запрещено: именно молчаливое допущение породило исходную задачу.

AC-6: полный pytest зелёный + догфуд: заблокированный коммит проходит.

## Plan

## Rollback

git revert коммита. Правка сводится к замене OR-двух-токенизаторов на один вызов shell_channel; откат возвращает прежнюю функцию целиком. Пины push-гейта не переписываются, поэтому регресс был бы виден сразу.

## Journal

- 2026-07-24T12:27:00Z [implementation] — Root cause (logic-error): при закрытии PowerShell-канала я заменил один токенизатор на ДИЗЪЮНКЦИЮ двух — «блокировать, если push увидел любой». Формулировка выглядит как ужесточение (нельзя уклониться, выбрав другой инструмент) и является ослаблением по ложным срабатываниям: каждый диалект неверно читает синтаксис другого, поэтому при расхождении выигрывает НЕКОМПЕТЕНТНЫЙ судья. POSIX-лексер не знает here-string PowerShell, ломается на апострофе внутри тела, после чего слова `git push --force` из ПРОЗЫ commit-сообщения становятся отдельными токенами и гейт требует push-тикет на обычный коммит. Prevention: дизъюнкция независимых судей корректна только там, где каждый судья КОМПЕТЕНТЕН на всём входе. Для диалектов это неверно по определению — компетенция определяется именно диалектом. Правило: когда вход имеет диалект, судью выбирают ПО ДИАЛЕКТУ (одна карта, здесь shell_channel), а не опрашивают всех. Дизъюнкция уместна для судей одного языка с разными эвристиками, конъюнкция — для подтверждения. Проверочный вопрос перед OR: «может ли один из судей ошибаться на входе, который другой читает верно?» Если да, OR превращает силу в ложное срабатывание. Отдельно: очевидная альтернативная починка через scan_target проверена и отвергнута ПИНОМ (`python -c "print('git push')"`), потому что она склеивает payload интерпретатора сырьём и обменяла бы один ложный блок на другой — альтернативу надо не отвергать рассуждением, а запинывать тестом.
- 2026-07-24T12:47:00Z [implementation] — AC-1 воспроизведение на РЕАЛЬНОМ теле заблокированного коммита (апостроф в слове PowerShell's плюс слова git push в прозе): tests/test_powershell_channel.py::TestPushGateFollowsTheToolsDialect::test_a_here_string_commit_message_is_not_a_push. AC-2 токенизация через shell_channel.tokenize по tool_name — та же единственная карта диалектов, что у write_targets и scan_target; пин, что гейт не выбирает диалект руками: tests/test_powershell_channel.py::TestPushGateFollowsTheToolsDialect::test_the_gate_does_not_choose_a_dialect_by_hand. AC-3 настоящий push ловится на обоих каналах: tests/test_powershell_channel.py::TestPushGateFollowsTheToolsDialect::test_a_real_push_is_still_gated_on_both_channels (параметры Bash и PowerShell); прежние пины git_push_gate зелёные без правок. AC-4 негативные пины на ложный блок: tests/test_powershell_channel.py::TestPushGateFollowsTheToolsDialect::test_a_mention_is_not_a_push. AC-5 остаточная граница обёртки решена и названа в docs/ru/enforcement-coverage.md и docs/en/enforcement-coverage.md: обычный push внутри payload обёртки тикета не требует, force-push там по-прежнему ловит bash_firewall со спуском в payload. AC-6 полный pytest 5750 passed, 23 skipped; verification_run #1278 pytest PASS 8656 ms; ruff по scripts/hooks чист; mypy 16 ошибок — все преэкзистующие, ни одной в новых модулях, счёт не вырос.
