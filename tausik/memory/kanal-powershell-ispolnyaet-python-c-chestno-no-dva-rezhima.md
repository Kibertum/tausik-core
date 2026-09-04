---
slug: kanal-powershell-ispolnyaet-python-c-chestno-no-dva-rezhima
title: "Канал PowerShell исполняет python -c честно, но ДВА режима ломают команду: вложенные двойные кавычки (громко) и $-подстановка в двойных кавычках (тихо)"
type: gotcha
tags:
  - powershell
  - premise
  - tooling
  - windows
task: powershell-channel-cannot-read-python-dash-c
edges: []
---

Замер #213 по девяти формам (журнал powershell-channel-cannot-read-python-dash-c) плюс поправка внешнего L3 #38. stdout отдаётся, $LASTEXITCODE честный, кириллица под -X utf8 в порядке. Режим 1 (громкий): Windows PowerShell 5.1 искажает `\"` и съедает внутренние двойные кавычки в аргументе нативного процесса — SyntaxError, rc=1. Режим 2 (ТИХИЙ): `$env:X`, `$(...)` и обратные кавычки внутри двойных кавычек подставляются PowerShell ДО запуска python — исполняется не та программа, stdout непуст, rc=0, и об этом ничего не сообщается; вызывающий читает замер программы, которую не писал. Формы «пустой stdout при rc=0» среди девяти нет. Правило: любую однострочную проверку с кавычками, $ или обратными кавычками писать ФАЙЛОМ (или одинарные кавычки снаружи без вложенных двойных). Supersedes #585.
