---
slug: razdelitel-puti-prinadlezhit-dialektu-a-ne-obschemu
title: "Разделитель пути принадлежит ДИАЛЕКТУ, а не общему резолверу: обратная косая — путь в PowerShell на любом хосте и экранирование в POSIX"
type: convention
tags:
  - dialect
  - posix
  - powershell
  - write-gate
task: pwsh-channel-backslash-script-path-unresolved-on-posix
edges: []
---

Пайплайн #6658: python .\helper.py прошёл гейт записи с 0 на Linux — диалект PowerShell отдал токен как есть, общий резолвер сделал os.path.join, на POSIX файла «.\helper.py» нет, fail-soft превратил «не найден» в «ничего не пишет». Правило: то, что значит символ в командной строке, знает диалект, и только он переписывает путь для хоста (os.sep) до общего резолвера; в Bash тот же символ съедает shlex, поэтому «утечка» в общий резолвер там ненаблюдаема — контроль на утечку ставь ДО лексера Bash. Граница: на Windows os.sep есть обратная косая, любая мутация замены не видна — юнит-тест пиннит os.sep на «/», а живой прогон делается на Linux. Тест из #201 замерялся на одной ОС; «5 из 5 написаний» на Windows не есть 5 из 5 на posix.
