---
slug: pwsh-here-string-body-parsed-as-commands
title: "PowerShell here-string @'...'@ разбирается как команды: `->` в тексте рождает фантомную цель записи и блокирует честную работу"
status: done
epic: null
story: null
complexity: medium
role: developer
stack: python
tier: null
call_budget: null
defect_of: powershell-tool-bypasses-bash-firewall
scope: "scripts/hooks/pwsh_cmd_parse.py, scripts/hooks/pwsh_write_parse.py, tests/test_powershell_channel.py, CHANGELOG.md, CHANGELOG.ru.md"
scope_exclude: "POSIX-ветка (bash_write_parse._strip_heredocs) — она уже верна и служит образцом, а не целью правки"
relevant_files:
  - "scripts/hooks/pwsh_cmd_parse.py"
  - "tests/test_powershell_channel.py"
  - "docs/ru/enforcement-coverage.md"
  - "docs/en/enforcement-coverage.md"
  - CHANGELOG.md
  - CHANGELOG.ru.md
  - "docs/_generated/constants.json"
scope_paths: []
scope_tools: []
depends_on: []
completed_at: "2026-07-24T12:21:38Z"
---

## Goal

defect_of powershell-tool-bypasses-bash-firewall, найден догфудингом НЕМЕДЛЕННО после закрытия: гейт заблокировал собственный `git commit -m @'...'@` этой же задачи.

`pwsh_cmd_parse.tokenize` не знает про here-string PowerShell (`@'...'@` и `@"..."@`). Тело here-string — ДАННЫЕ, но разбирается как живая командная строка, поэтому любой `->` в прозе даёт токены `-`, `>`, `<слово>`, оператор `>` читается как редирект, а следующее слово — как цель записи. Наблюдённый блок: цели `-`, `bypassed`, `@` из текста commit-сообщения, содержавшего «384 -> 128 строк».

POSIX-сторона выучила ровно этот урок и несёт `_strip_heredocs` с прямым описанием симптома в докстринге: «a bare `>` or `->` in prose/code inside the body manufactures a phantom redirect target (`def f() -> int:` -> target `int:`), which then blocks an otherwise-compliant write». Новый диалект получил детекторы, но не получил этой защиты — паритет каналов соблюдён по ПРАВИЛАМ и нарушен по ЗАЩИТАМ ОТ ЛОЖНЫХ СРАБАТЫВАНИЙ.

Цена высокая и асимметричная (конв. #291): это не пропуск, а ЛОЖНЫЙ БЛОК на самой частой операции — многострочное сообщение коммита. Единственный выход, который сообщение предлагает агенту, — начать задачу или обойти хук; и то и другое тренирует обход. Ровно тот механизм, из-за которого memory_pretool_block сознательно не принимает regex-fallback.

Смежное: `_strip_heredocs` в bash_write_parse держит ЗАГОЛОВОК строки (чтобы реальная цель `cat > f <<EOF` осталась видна) и выбрасывает только тело — то же различение нужно здесь: `@'...'@ | Out-File x.txt` пишет в x.txt, и это должно остаться видимым.</goal>
<parameter name="acceptance_criteria">AC-1 (воспроизведение, падает на текущем коде): write_targets на `git commit -m @'...'@`, чьё тело содержит `->` и `>`, сейчас возвращает непустой список фантомных целей. Пин на конкретную строку из реального коммита сессии #134.

AC-2: tokenize понимает обе формы here-string — `@'` … `'@` (литеральная) и `@"` … `"@` (интерполирующая). Тело — ОДИН токен. Терминатор `'@`/`"@` признаётся только в начале строки (как требует сам PowerShell), иначе апостроф-собака внутри текста закроет строку раньше времени — это тот же дефект, что POSIX-сторона поймала на индентированном псевдо-терминаторе heredoc'а.

AC-3: реальная цель за here-string НЕ теряется: `@'...'@ | Out-File notes.md`, `Set-Content -Value @'...'@ -Path notes.md` — цель notes.md по-прежнему видна. Это отличает фикс от тупого «выбросить всё после @'».

AC-4 (тот же вопрос ко второму судье): проверить, не рождает ли тело here-string ЛОЖНОГО срабатывания в bash_firewall — BLOCKED_PATTERNS матчатся подстрокой, и текст про `Format-Volume` или `DROP TABLE` внутри commit-сообщения не должен блокировать. Если рождает — закрыть тем же швом.

AC-5 (негативные пины): реальные команды не перестали ловиться. `@'...'@` не должен становиться способом спрятать команду: `iex @'...'@` — payload по-прежнему разбирается.

AC-6: аудит остальных PowerShell-конструкций-данных того же класса на предмет такой же слепоты (`@(...)`, `$(...)`, блоки `{...}`), с решением по каждой — закрыть или назвать остаточной границей.

AC-7: полный pytest зелёный.</acceptance_criteria>
<parameter name="complexity">medium

## Acceptance Criteria

AC-1 (воспроизведение, падает на текущем коде): write_targets на `git commit -m @'...'@`, чьё тело содержит `->` и `>`, сейчас возвращает непустой список фантомных целей. Пин на конкретную строку из реального коммита сессии #134 («384 -> 128 строк»), а не на выдуманный пример.

AC-2: tokenize понимает обе формы here-string — `@'` … `'@` (литеральная) и `@"` … `"@` (интерполирующая). Тело — ОДИН токен. Терминатор `'@`/`"@` признаётся ТОЛЬКО в начале строки, как требует сам PowerShell; иначе последовательность апостроф-собака внутри текста закроет строку раньше времени и снова выпустит остаток тела как живой shell — это ровно тот дефект, который POSIX-сторона поймала на индентированном псевдо-терминаторе heredoc'а.

AC-3: реальная цель ЗА here-string не теряется: `@'...'@ | Out-File notes.md` и `Set-Content -Value @'...'@ -Path notes.md` — notes.md по-прежнему видна. Это отличает фикс от тупого «выбросить всё после @'».

AC-4 (тот же вопрос второму судье): проверить, не рождает ли тело here-string ложного срабатывания в bash_firewall — BLOCKED_PATTERNS матчатся ПОДСТРОКОЙ, поэтому слова `Format-Volume` или `DROP TABLE` внутри commit-сообщения не должны блокировать. Если рождает — закрыть тем же швом, а не отдельной заплатой.

AC-5 (негативные пины): here-string не становится способом спрятать команду. `iex @'...'@` — payload по-прежнему разбирается; реальные wipe/push по-прежнему ловятся; 79 существующих пинов канала PowerShell зелёные без правок.

AC-6: аудит остальных PowerShell-конструкций того же класса (`@(...)`, `$(...)`, блоки `{...}`) на такую же слепоту, с решением по каждой — закрыть или назвать остаточной границей в enforcement-coverage.md. Молчание запрещено.

AC-7: полный pytest зелёный + догфуд-проверка: тот самый коммит, который был заблокирован, проходит.

## Plan

## Rollback

git revert коммита. Правка аддитивна: обработка here-string — отдельная ветка в токенизаторе, её удаление возвращает прежнее поведение. Существующие пины канала PowerShell (79 тестов) не переписываются, поэтому регресс был бы виден немедленно.

## Journal

- 2026-07-24T12:20:47Z [implementation] — AC-1 воспроизведение на РЕАЛЬНОЙ строке заблокированного коммита: tests/test_powershell_channel.py::TestHereStringBodyIsData::test_a_here_string_commit_message_writes_nothing. Механизм установлен эмпирически (probe): тело держится случайно, но апостроф внутри тела рвёт разбор -> tokenize=None -> regex-fallback -> фантомные цели ['bypassed']. AC-2 обе формы + терминатор только в начале строки: ::test_interpolating_here_string_too, ::test_terminator_is_only_recognised_at_line_start (единственный из 8, падавший до фикса). AC-3 реальная цель за here-string не теряется: ::test_a_real_target_after_a_here_string_is_still_seen. AC-4 второй судья: ::test_a_dangerous_phrase_quoted_in_a_commit_message_is_not_a_command (Format-Volume/DROP TABLE/mkfs.ext4 в теле сообщения rc=0). AC-5 here-string не стал способом спрятать команду: ::test_a_here_string_does_not_hide_a_command_from_the_firewall (iex @'...'@ по-прежнему разбирается); 79 прежних пинов канала зелёные без правок. AC-6 аудит конструкций-данных таблицей в docs/{ru,en}/enforcement-coverage.md: here-string закрыт, кавычки закрыты, script-блоки сознательно НЕ данные (исполняются), \/@(...) названы остатком. AC-7 полный pytest 5744 passed 23 skipped; verification_run #1275 pytest PASS 8905 ms.
- 2026-07-24T12:21:10Z [implementation] — Root cause (edge-case): токенизатор нового диалекта не знал конструкции here-string PowerShell (@'...'@ / @"..."@). Тело держалось в одном токене СЛУЧАЙНО — за счёт того, что открывающая и закрывающая кавычки образуют пару, — и рассыпалось, как только внутри тела встречался апостроф. Тогда tokenize возвращал None, срабатывал regex-fallback, который ПЕРЕобнаруживает по замыслу, и одиночный `>` в прозе commit-сообщения становился редиректом с фантомной целью. Глубже: детекторы для нового канала были перенесены с POSIX-стороны, а ЗАЩИТЫ ОТ ЛОЖНЫХ СРАБАТЫВАНИЙ — нет. У POSIX-близнеца ровно от этого симптома есть _strip_heredocs, и симптом описан в его докстринге дословно. Получился паритет каналов по правилам и пробел по защитам, причём в дорогую сторону: не пропуск, а ложный блок на самой рутинной операции. Prevention: перенося детекторы на новый канал, переноси ВМЕСТЕ С НИМИ список ложных срабатываний, который старый канал уже оплатил. Практический приём: прочитать докстринги защитных функций донорского диалекта (_strip_heredocs, _plausible_path, _PAYLOAD) и для каждой спросить «что в новом диалекте играет эту роль» — здесь ответом было «here-string», и вопрос никто не задал. Проверочный признак готовности: детектор умеет отличать текст от команды в КАЖДОЙ конструкции-носителе данных, а не в одной; аудит по одной конструкции теперь зафиксирован таблицей в docs/{ru,en}/enforcement-coverage.md. Дополнительно: regex-fallback обязан считаться подозрительным результатом — он сработал здесь не как страховка, а как источник ложного блока.
- 2026-07-24T12:21:36Z [implementation] — AC-1 воспроизведение на РЕАЛЬНОЙ строке заблокированного коммита: tests/test_powershell_channel.py::TestHereStringBodyIsData::test_a_here_string_commit_message_writes_nothing. Механизм установлен эмпирически: тело держится случайно, апостроф внутри тела рвёт разбор -> tokenize=None -> regex-fallback -> фантомная цель 'bypassed'. AC-2 обе формы here-string и терминатор только в начале строки: tests/test_powershell_channel.py::TestHereStringBodyIsData::test_interpolating_here_string_too и ::test_terminator_is_only_recognised_at_line_start (единственный из восьми, падавший до фикса). AC-3 реальная цель за here-string не теряется: tests/test_powershell_channel.py::TestHereStringBodyIsData::test_a_real_target_after_a_here_string_is_still_seen. AC-4 второй судья не блокирует опасную фразу в теле сообщения: tests/test_powershell_channel.py::TestHereStringBodyIsData::test_a_dangerous_phrase_quoted_in_a_commit_message_is_not_a_command. AC-5 here-string не стал укрытием: tests/test_powershell_channel.py::TestHereStringBodyIsData::test_a_here_string_does_not_hide_a_command_from_the_firewall, плюс 79 прежних пинов канала зелёные без правок. AC-6 аудит конструкций-данных таблицей в docs/ru/enforcement-coverage.md и docs/en/enforcement-coverage.md: here-string закрыт, кавычки закрыты, script-блоки сознательно НЕ данные (они исполняются), подвыражения названы остаточной границей. AC-7 полный pytest 5744 passed, 23 skipped; verification_run #1275 pytest PASS 8905 ms.
